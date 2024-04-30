#!/usr/bin/env python
#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Chocolatey Automatic Package Updater

import io
import re
import subprocess
from hashlib import sha256

import requests
import yaml
from bs4 import BeautifulSoup
from jinja2 import Template
from loguru import logger

with open("settings/config.yaml", "r") as ymlfile:
    cfg = yaml.load(ymlfile, Loader=yaml.SafeLoader)

if cfg['config']['logging']['file_log_enabled']:
    logger.add(cfg['config']['logging']['file_log_path'], level="DEBUG", format="{time} {level} {message}", rotation="16 KB", compression="zip")


class Program:
    def __init__(self, app):
        self.app = app
        self.response_git = requests.get(f"https://api.github.com/repos/{self.app['owner']}/{self.app['repo']}/releases/latest")
        self.response_choco = requests.get(f"https://community.chocolatey.org/packages/{self.app['repo']}")

    def get_git_ver(self):
        git_ver = self.response_git.json()["tag_name"]
        return git_ver

    def get_choco_ver(self):
        soup = BeautifulSoup(self.response_choco.text, "lxml")        
        title_tag = soup.find("title")
        title_text = title_tag.get_text()
        choco_ver = re.search(r'(\d+\.\d+\.\d+)', title_text).group(0)
        return choco_ver
        # soup = BeautifulSoup(self.response_choco.text, "lxml")
        # td_tag = soup.find("td", class_="version")
        # span_tag = td_tag.find("span") 
        # choco_ver = (re.search(r'(?P<ver>\d+\.\d+\.\d+)', span_tag.text)).group(0)
        # # page_items = soup.find_all("span", class_="ms-2")
        # # choco_ver = (re.search(self.app["regexp_mask"]["choco_ver"], str(page_items))).group(0)
        # return choco_ver

    def get_checksum(self, url):
        inmemfile = io.BytesIO(requests.get(url).content)
        checksum = sha256(inmemfile.getbuffer()).hexdigest()
        inmemfile.close()
        return checksum

    def form_template_vars(self):
        windows = list(
            filter(
                lambda platform: platform["content_type"] == "application/x-msdownload",
                self.response_git.json()["assets"],
            )
        )
        url_32 = ((windows)[1])["browser_download_url"]
        url_64 = ((windows)[4])["browser_download_url"]

        # checksum_32 = (re.search(self.app["regexp_mask"]["checksum_32"], str(self.response_git.json()["body"]))).group(1)
        # checksum_64 = (re.search(self.app["regexp_mask"]["checksum_64"], str(self.response_git.json()["body"]))).group(1)
        checksum_32 = self.get_checksum(url_32)
        checksum_64 = self.get_checksum(url_64)        

        changelog = (re.search(self.app["regexp_mask"]["changelog_prepare"], str(self.response_git.json()["body"]))).group(0)
        changelog = re.findall(self.app["regexp_mask"]["changelog_final"], changelog, re.MULTILINE)
        changelog = str("\n".join(changelog))

        dict_provision = {
            "id": self.app["id"],
            "title": self.app["title"],
            "authors": self.app["authors"],
            "projectUrl": self.app["projectUrl"],
            "iconUrl": self.app["iconUrl"],
            "licenseUrl": self.app["licenseUrl"],
            "tags": self.app["tags"],
            "summary": self.app["summary"],
            "description": self.app["description"],
            "url_32": url_32,
            "url_64": url_64,
            "checksumType": self.app["checksumType"],
            "checksum_32": checksum_32,
            "checksum_64": checksum_64,
            "silentArgs": self.app["silentArgs"],
            "version": self.get_git_ver(),
            "changelog": changelog
        }

        return dict_provision


def write_manifests(template_file, manifest):
    file = open(f"templates/{template_file}").read()
    template = Template(file)
    file = open(manifest, "w")
    file.write(template.render(**dict_provision))
    file.close()


def run_command(command):
    cmd = command
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)
    return result.stdout.decode("utf-8").rstrip()


if __name__ == "__main__":
    for app_name, app in cfg['config']['programs'].items():
        target_program = Program(app)
        # print(target_program.app)

        if target_program.get_git_ver() == target_program.get_choco_ver():    
            print("No updates. Time to drunch!")
        else:
            print("Oh no! Time to new build! Go ahead!")
            
            dict_provision = target_program.form_template_vars()
            write_manifests("chocolateyinstall.template", "fitter/tools/chocolateyinstall.ps1")
            write_manifests("nuspec.template", f"fitter/{target_program.app['repo'].lower()}.nuspec")

            # logger.debug(run_command("cd fitter/ && choco pack"))
            # run_command(f'cd fitter/ && choco push {target_program.repo.lower()}.{git_ver}.nupkg --source https://push.chocolatey.org/') # uncomment for prod

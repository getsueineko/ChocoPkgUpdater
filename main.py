import re
import subprocess

import requests
import yaml
from bs4 import BeautifulSoup
from jinja2 import Template
from loguru import logger


with open("settings/config.yaml", "r") as ymlfile:
    cfg = yaml.load(ymlfile, Loader=yaml.SafeLoader)

logger.add("logs/debug.log", level="DEBUG", format="{time} {level} {message}", rotation="1 MB", compression="zip")


class Program:
    def __init__(self, owner, repo):
        self.owner = owner
        self.repo = repo
        self.response_git = requests.get(f"https://api.github.com/repos/{owner}/{repo}/releases/latest")
        self.response_choco = requests.get(f"https://community.chocolatey.org/packages/{repo}")

    def get_git_ver(self):
        git_ver = self.response_git.json()["tag_name"]
        return git_ver

    def get_choco_ver(self):
        soup = BeautifulSoup(self.response_choco.text, "lxml")
        page_items = soup.find_all("span", class_="ms-2")
        choco_ver = (re.search(cfg["regexp_mask"]["choco_ver"], str(page_items))).group(0)
        return choco_ver

    def form_templatevars(self):
        windows = list(
            filter(
                lambda platform: platform["content_type"] == "application/x-ms-dos-executable",
                self.response_git.json()["assets"],
            )
        )
        url_32 = ((windows)[0])["browser_download_url"]
        url_64 = ((windows)[1])["browser_download_url"]

        checksum_32 = (re.search(cfg["regexp_mask"]["checksum_32"], str(self.response_git.json()["body"]))).group(1)
        checksum_64 = (re.search(cfg["regexp_mask"]["checksum_64"], str(self.response_git.json()["body"]))).group(1)

        changelog = (re.search(cfg["regexp_mask"]["changelog_prepare"], str(self.response_git.json()["body"]))).group(0)
        changelog = re.findall(cfg["regexp_mask"]["changelog_final"], changelog, re.MULTILINE)
        changelog = str("\n".join(changelog))

        dict_provision = {
            "url_32": url_32,
            "url_64": url_64,
            "checksum_32": checksum_32,
            "checksum_64": checksum_64,
            "version": self.get_git_ver(),
            "changelog": changelog,
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
    target_program = Program(cfg["program"]["owner"], cfg["program"]["repo"])

    if target_program.get_git_ver() == target_program.get_choco_ver():
        print("No updates. Time to drunch!")
    else:
        print("Oh no! Time to new build! Go ahead!")

        dict_provision = target_program.form_templatevars()
        write_manifests("chocolateyinstall.template", "fitter/tools/chocolateyinstall.ps1")
        write_manifests("nuspec.template", f"fitter/{target_program.repo.lower()}.nuspec")

        logger.debug(run_command("cd fitter/ && choco pack"))
        # run_command(f'cd fitter/ && choco push {target_program.repo.lower()}.{git_ver}.nupkg --source https://push.chocolatey.org/') # uncomment for prod

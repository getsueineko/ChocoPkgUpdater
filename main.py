import re
import subprocess

import requests
from bs4 import BeautifulSoup
from jinja2 import Template
from loguru import logger


OWNER = "zaps166"
REPO = "QMPlay2"


logger.add("logs/debug.log", level="DEBUG", format="{time} {level} {message}", rotation="1 MB", compression="zip")


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


def form_templatevars():
    windows = list(
        filter(
            lambda platform: platform["content_type"] == "application/x-ms-dos-executable",
            response_git.json()["assets"],
        )
    )
    url_32 = ((windows)[0])["browser_download_url"]
    url_64 = ((windows)[1])["browser_download_url"]

    checksum_32 = (re.search(r"(.{40})\s\sQMPlay2-Win(32)-\d", str(response_git.json()["body"]))).group(1)
    checksum_64 = (re.search(r"(.{40})\s\sQMPlay2-Win(64)-\d", str(response_git.json()["body"]))).group(1)

    changelog = (re.search(r".*Changes.+\n(.*\n)*---", str(response_git.json()["body"]))).group(0)
    # changelog = (re.search(r'.*Change.*\n(.*\n)*\n', str(response_git.json()['body']))).group(0)
    changelog = re.findall(r"^(?!.*Linux|.*KDE|.*Changes).*,", changelog, re.MULTILINE)
    changelog = str("\n".join(changelog))

    dict_provision = {
        "url_32": url_32,
        "url_64": url_64,
        "checksum_32": checksum_32,
        "checksum_64": checksum_64,
        "version": git_ver,
        "changelog": changelog,
    }

    return dict_provision


if __name__ == "__main__":
    response_git = requests.get(f"https://api.github.com/repos/{OWNER}/{REPO}/releases/latest")
    git_ver = response_git.json()["tag_name"]

    response_choco = requests.get(f"https://community.chocolatey.org/packages/{REPO}")
    soup = BeautifulSoup(response_choco.text, "lxml")
    page_items = soup.find_all("span", class_="ms-2")
    logger.debug(page_items)
    choco_ver = (re.search(r"\d{2}\.\d{2}\.\d{2}", str(page_items))).group(0)

    if git_ver == choco_ver:
        print("No updates. Time to drunch!")
    else:
        print("Oh no! Time to new build! Go ahead!")
        
        dict_provision = form_templatevars()
        write_manifests("chocolateyinstall.template", "fitter/tools/chocolateyinstall.ps1")
        write_manifests("nuspec.template", f"fitter/{REPO.lower()}.nuspec")

        logger.debug(run_command("cd fitter/ && choco pack"))
        # run_command(f'cd fitter/ && choco push {REPO.lower()}.{git_ver}.nupkg --source https://push.chocolatey.org/') # uncomment for prod

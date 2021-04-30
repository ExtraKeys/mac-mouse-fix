#!/usr/bin/python3


# Imports

import os
import shutil
# import requests # Only ships with python2 on mac it seems
import urllib.request
import urllib.parse

import json

from pprint import pprint

import subprocess

# Constants
#   Paths are relative to project root.

os.chdir('..') # Run this script from the Scripts folder, it will then automatically chdir to the root dir

releases_api_url = "https://api.github.com/repos/noah-nuebling/mac-mouse-fix/releases"

raw_github_url = "https://raw.githubusercontent.com/noah-nuebling/mac-mouse-fix/master"

appcast_file_name = "appcast.xml"
appcast_pre_file_name = "appcast-pre.xml"

appcast_url = f"{raw_github_url}/{appcast_file_name}"
appcast_pre_url = f"{raw_github_url}/{appcast_pre_file_name}"

info_plist_path = "App/SupportFiles/Info.plist"
base_xcconfig_path = "xcconfig/Base.xcconfig"
sparkle_project_path = "Frameworks/Sparkle-1.26.0" # This is dangerously hardcoded
download_folder = "generate_appcasts_downloads" # We want to delete this on exit
app_bundle_name = "Mac Mouse Fix.app"
prefpane_bundle_name = "Mouse Fix.prefpane"
info_plist_app_subpath = "Contents/Info.plist"
current_directory = os.getcwd()
download_folder_absolute = os.path.join(current_directory, download_folder)
files_to_checkout = [info_plist_path, base_xcconfig_path]


def generate():
    try:

        # Check if there are uncommited changes
        # This script uses git stash several times, so they'd be lost
        uncommitted_changes = subprocess.check_output('git diff-index HEAD --', shell=True).decode('utf-8')
        if (len(uncommitted_changes) != 0):
            raise Exception('There are uncommited changes. Please commit or stash them before running this script.')

        # Script

        request = urllib.request.urlopen(releases_api_url)
        releases = json.load(request)

        # We'll be iterating over all releases and collecting data to put into the appcast
        appcast_items = []
        appcast_pre_items = [] # Items for the pre-release channel

        for r in releases:

            # Accessing Xcode environment variables is night impossible it seems
            # The only way to do it I found is described here:
            #   https://stackoverflow.com/questions/6523655/how-do-you-access-xcode-environment-and-build-variables-from-an-external-scrip
            #   And that's not feasible to do for old versions.


            # Get short version
            short_version = r['name']

            print(f'Processing release {short_version}...')

            # Get release notes
            release_notes = r['body'] # This is markdown

            # Write release notes to file. As a plain string I had trouble passing it to pandoc, because I couldn't escape it properly
            os.makedirs(download_folder_absolute, exist_ok=True)
            text_file = open(f"{download_folder}/release_notes.md", "w")
            n = text_file.write(release_notes)
            text_file.close()
            # Convert to HTML
            release_notes = subprocess.check_output(f"cat {download_folder}/release_notes.md | pandoc -f markdown -t html", shell=True).decode('utf-8')
                # The $'' are actually super important, otherwise bash won't presever the newlines for some reason


            # Get title
            title = f"{short_version} available!"

            # Get publishing date
            publising_date = r['published_at'];

            # Get isPrerelease
            is_prerelease = r['prerelease']

            # Get type
            type = "application/octet-stream" # Not sure what this is or if this is right

            # Get localized release notes ?
            #   ...


            # Get tag
            tag_name = r['tag_name']

            # Get commit number
            # commit = os.system(f"git rev-list -n 1 {tag_name}") # Can't capture the output of this for some reason
            commit_number = subprocess.check_output(f"git rev-list -n 1 {tag_name}", shell=True).decode('utf-8')
            commit_number = commit_number[0:-1] # There's a linebreak at the end

            # Tried to checkout each commit and then read bundle version and minimum compatible macOS version from the local Xcode source files. 
            # I had trouble making this approach work, though, so we went over to just unzipping each update and reading that data directly from the bundle

            # # Check out commit
            # # This would probably be a lot faster if we only checked out the files we need
            # os.system("git stash")
            # files_string = ' '.join(files_to_checkout)
            # bash_string = f"git checkout {commit_number} {files_string}"
            # try:
            #     subprocess.check_output(bash_string)
            # except Exception as e:
            #     print(f"Exception while checking out commit {commit_number} ({short_version}): {e}. Skipping this release.")
            #     continue

            # # Get version
            # #   Get from Info.plist file
            # bundle_version = subprocess.check_output(f"/usr/libexec/PlistBuddy {info_plist_path} -c 'Print CFBundleVersion'", shell=True).decode('utf-8')

            # # Get minimum macOS version
            # #   The environment variable buried deep within project.pbxproj. No practical way to get at this
            # #   Instead, we're going to hardcode this for old versions and define a new env variable via xcconfig we can reference here for newer verisons
            # #   See how alt-tab-macos did it here: https://github.com/lwouis/alt-tab-macos/blob/master/config/base.xcconfig
            # minimum_macos_version = ""
            # try:
            #     minimum_macos_version = subprocess.check_output(f"awk -F ' = ' '/MACOSX_DEPLOYMENT_TARGET/ {{ print $2; }}' < {base_xcconfig_path}", shell=True).decode('utf-8')
            #     minimum_macos_version = minimum_macos_version[0:-1] # Remove trailing \n character
            # except:
            #     minimum_macos_version = 10.11

            # Get download link
            download_link = r['assets'][0]['browser_download_url']

            # Download update
            os.makedirs(download_folder_absolute, exist_ok=True)
            download_name = download_link.rsplit('/', 1)[-1]
            download_zip_path = f'{download_folder}/{download_name}'
            urllib.request.urlretrieve(download_link, download_zip_path)

            # Get edSignature
            signature_and_length = subprocess.check_output(f"./{sparkle_project_path}/bin/sign_update {download_zip_path}", shell=True).decode('utf-8')
            signature_and_length = signature_and_length[0:-1]

            # Unzip update
            os.system(f'ditto -V -x -k --sequesterRsrc --rsrc "{download_zip_path}" "{download_folder}"') # This works, while subprocess.check_output doesn't for some reason

            
            # Find app bundle
            # Maybe we could just name the unzipped folder instead of guessing here
            # Well we also use this to determine if the download is a prefpane or an app. There might be better ways to infer this but this should work
            is_prefpane = False
            app_path = f'{download_folder}/{app_bundle_name}'
            if not os.path.exists(app_path):
                app_path = f'{download_folder}/{prefpane_bundle_name}'
                if not os.path.exists(app_path):
                    raise Exception('Unknown bundle name after unzipping')
                else:
                    is_prefpane = True

            if is_prefpane:
                continue

            # Find Info.plist in app bundle
            info_plist_path = f'{app_path}/{info_plist_app_subpath}'

            # Read stuff from Info.plist
            bundle_version = subprocess.check_output(f"/usr/libexec/PlistBuddy '{info_plist_path}' -c 'Print CFBundleVersion'", shell=True).decode('utf-8')
            minimum_macos_version = subprocess.check_output(f"/usr/libexec/PlistBuddy '{info_plist_path}' -c 'Print LSMinimumSystemVersion'", shell=True).decode('utf-8')
            bundle_version = bundle_version[0:-1]
            minimum_macos_version = minimum_macos_version[0:-1]

            # Delete bundle we just processed so that we won't accidentally process it again next round (that happens if the next bundle has prefpane_bundle_name instead of app_bundle_name)
            shutil.rmtree(app_path)

            # Assemble collected data into appcast-ready item-string
            item_string = f"""\
    <item>
        <title>{title}</title>
        <pubDate>{publising_date}</pubDate>
        <sparkle:minimumSystemVersion>{minimum_macos_version}</sparkle:minimumSystemVersion>
        <description><![CDATA[
            {release_notes}
        ]]>
        </description>
        <enclosure
            url=\"{download_link}\"
            sparkle:version=\"{bundle_version}\"
            sparkle:shortVersionString=\"{short_version}\"
            {signature_and_length}
            type=\"{type}\"
        />
    </item>"""

            # Append item_string to arrays
            appcast_pre_items.append(item_string)
            if not is_prerelease:
                appcast_items.append(item_string)

            print(item_string)

        # Clean up downloaded files
        clean_up(download_folder)

        # Assemble item strings into final appcast strings


        appcast_format_string = '''\
<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:sparkle="http://www.andymatuschak.org/xml-namespaces/sparkle"  xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>Mac Mouse Fix Update Feed</title>
    <link>{}</link>
    <description>Stable releases of Mac Mouse Fix</description>
    <language>en</language>
    {}
  </channel>
</rss>'''

        appcast_pre_format_string = '''\
<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:sparkle="http://www.andymatuschak.org/xml-namespaces/sparkle"  xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>Mac Mouse Fix Update Feed for Prereleases</title>
    <link>{}</link>
    <description>Prereleases of Mac Mouse Fix</description>
    <language>en</language>
    {}
  </channel>
</rss>'''
        items_joined = '\n'.join(appcast_items)
        appcast_content_string = appcast_format_string.format(appcast_url, items_joined)
        pre_items_joined = '\n'.join(appcast_pre_items)
        appcast_pre_content_string = appcast_pre_format_string.format(appcast_pre_url, pre_items_joined)

        # Write to file

        file1 = open(appcast_file_name,"w")
        L = file1.write(appcast_content_string)
        file1.close()

        file2 = open(appcast_pre_file_name,"w")
        L = file2.write(appcast_pre_content_string)
        file2.close()


    except Exception as e: # Exit immediately if anything goes wrong
        print(e)
        clean_up(download_folder)
        exit(1)

def clean_up(download_folder):
    if download_folder != "":
        try:
            os.system(f'rm -R {download_folder}')
        except:
            pass

generate()
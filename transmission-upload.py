#!/usr/bin/env python3
import os
import subprocess
import logging
import argparse
import shutil

# Configurable Paths
UPLOAD_DIR = '/mnt/user/data/uploads/torrents/'
TORRENT_OUTPUT_DIR = '/mnt/user/data/uploads/torrents'

# Transmission Docker Config
TRANSMISSION_CONTAINER = "transmission"
TRANSMISSION_UID = "1000"

def setup_logging(log_file):
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    print(f"Logging to {log_file}")

def create_hardlinks(source, destination):
    try:
        # Ensure the parent directory exists
        parent_dir = os.path.dirname(destination)
        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir)
            logging.info(f"Created parent directory: {parent_dir}")

        if not os.path.exists(destination):
            os.makedirs(destination)
            logging.info(f"Created directory: {destination}")

        for root, dirs, files in os.walk(source):
            rel_path = os.path.relpath(root, source)
            dest_path = os.path.join(destination, rel_path)

            if not os.path.exists(dest_path):
                os.makedirs(dest_path)
                logging.info(f"Created directory: {dest_path}")

            for file in files:
                src_file = os.path.join(root, file)
                dest_file = os.path.join(dest_path, file)

                if not os.path.exists(dest_file):
                    os.link(src_file, dest_file)
                    logging.info(f"Created hardlink: {dest_file} -> {src_file}")
                else:
                    logging.warning(f"File already exists: {dest_file}")
    except Exception as e:
        logging.error(f"Error during hardlink creation: {e}")
        print(f"Error: {e}")

def generate_torrent(target_folder, dest_path):
    try:
        # Use the selected folder's name as the torrent name
        folder_name = os.path.basename(os.path.normpath(target_folder))
        torrent_name = f"{folder_name}.torrent"
        torrent_path = os.path.join(TORRENT_OUTPUT_DIR, torrent_name)

        # Prompt for tracker URLs
        trackers = input("Enter tracker URLs (comma separated):").strip().split(',')
        tracker_args = []
        for tracker in trackers:
            tracker_args.extend(["-t", tracker.strip()])

        # Prompt for torrent source
        torrent_source = input("Enter torrent tracker (any identifier, e.g., tracker name or URL):").strip()

        # Prompt for private or public torrent
        is_private = input("Should the torrent be private? (yes/no, default: yes):").strip().lower() or "yes"
        private_flag = ["-p"] if is_private == "yes" else []

        # Adjust path for Docker container
        container_target_folder = target_folder.replace('/mnt/user/', '/user/')
        torrent_path = torrent_path.replace('/mnt/user/', '/user/')

        # Run transmission-create inside the Docker container
        cmd = [
            "docker", "exec", "-u", TRANSMISSION_UID, TRANSMISSION_CONTAINER,
            "transmission-create", "-o", torrent_path, "--source", torrent_source
        ] + private_flag + tracker_args + [container_target_folder]

        subprocess.run(cmd, check=True)
        logging.info(f"Torrent created: {torrent_path}")
        print(f"✅ Torrent created: {torrent_path}")

        # Move the torrent file to the hardlinked directory
        final_torrent_path = os.path.join(dest_path, torrent_name)
        shutil.move(torrent_path, final_torrent_path)
        logging.info(f"Torrent file moved to: {final_torrent_path}")
        print(f"📦 Torrent file moved to: {final_torrent_path}")

    except subprocess.CalledProcessError as e:
        logging.error(f"Error creating torrent: {e}")
        print(f"Error: {e}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        print(f"Error: {e}")

def main():
    parser = argparse.ArgumentParser(description="Create hardlinks and generate a torrent file using Transmission inside a Docker container.")
    parser.add_argument('source_path', type=str, help="Path to the source music folder.")
    parser.add_argument('--log-file', type=str, default='create_torrent.log', help="Path to the log file.")
    args = parser.parse_args()

    setup_logging(args.log_file)

    source_path = os.path.abspath(args.source_path)
    if not os.path.exists(source_path):
        print(f"Error: Source folder not found: {source_path}")
        logging.error(f"Source folder not found: {source_path}")
        return

    # Mirror the directory structure in UPLOAD_DIR
    rel_path = os.path.relpath(source_path, '/mnt/user/data/media')
    dest_path = os.path.join(UPLOAD_DIR, rel_path)

    print(f"Creating hardlinks from {source_path} to {dest_path}...")
    create_hardlinks(source_path, dest_path)

    print(f"Generating torrent for {dest_path}...")
    generate_torrent(source_path, dest_path)

    print("🎉 All done!")

if __name__ == "__main__":
    main()
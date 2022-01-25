# python3 archive.py 2> /dev/null &
#
# Remove recorded footage, GPX logs, and other files until their total size is less than the maximum
# capacity.
#
import argparse
import os
import re
import signal
import sys
import traceback

import ivr


def remove(file, reason=None):
    os.remove(file)
    reason = "" if reason is None else " ({})".format(reason)
    ivr.log("file removed: {}{}".format(file, reason))


# Remote files with older timestamps so that the total size of files with filenames of the
# specified pattern doesn't exceed the maximum capacity (but the least min_fises remain).
def ensure_storage_space(dir, file_pattern, max_capacity, min_files):

    # retrie all footage files and sort them in order of newest to oldest
    files = []
    for f in os.listdir(dir):
        if re.fullmatch(file_pattern, f):
            file = os.path.join(dir, f)
            if os.path.getsize(file) == 0:
                # remove if the file is empty
                reason = "empty file"
                remove(file, reason)
            else:
                files.append((os.stat(file).st_mtime, file))
    files.sort(reverse=True)
    files = [f for _, f in files]

    # exclude the latest files from being removed
    total_size = 0
    for _ in range(min_files):
        if len(files) == 0:
            break
        else:
            file = files.pop(0)
            total_size += os.path.getsize(file)

    # remove old files that have exceeded storage capacity
    for file in files:
        if total_size + os.path.getsize(file) > max_capacity:
            remove(file, "exceeding the storage capacity")
        else:
            total_size += os.path.getsize(file)

    return


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert and remove recorded footage files"
    )
    parser.add_argument(
        "-d",
        "--dir",
        metavar="DIR",
        default=ivr.data_dir(),
        help="Directory where the footage and other files are stored (default: {})".format(
            ivr.data_dir()
        ),
    )
    parser.add_argument(
        "-lf",
        "--limit-footage",
        metavar="CAPACITY",
        default="60G",
        help="Total size of footage file to be retained, such as 32G, 32000M (default: 60G)",
    )
    parser.add_argument(
        "-lt",
        "--limit-tracklog",
        metavar="CAPACITY",
        default="2G",
        help="Total size of track log file to be retained, such as 32G, 32000M (default: 2G)",
    )
    parser.add_argument(
        "-i",
        "--interval",
        metavar="SECONDS",
        type=int,
        default=20,
        help="Interval at which to monitor the directory (default: 20 sec)",
    )

    try:

        # register SIGTERM handler
        signal.signal(signal.SIGTERM, ivr.term_handler)
        signal.signal(signal.SIGINT, ivr.term_handler)

        args = parser.parse_args()
        dir = args.dir
        limit_footage = ivr.without_aux_unit(args.limit_footage)
        limit_tracklog = ivr.without_aux_unit(args.limit_tracklog)
        interval = args.interval

        while True:
            ensure_storage_space(dir, ivr.FOOTAGE_FILE_PATTERN, limit_footage, 2)
            ensure_storage_space(dir, ivr.TRACKLOG_FILE_PATTERN, limit_tracklog, 2)
            time.sleep(interval)

    except ivr.TermException as e:
        ivr.log("IVR terminates the cleaning")
        ivr.beep("cleaning has stopped")
    except Exception as e:
        t = "".join(list(traceback.TracebackException.from_exception(e).format()))
        ivr.log("ERROR: {}".format(t))
        ivr.log("IVR terminates the cleaning by an error")
        ivr.beep("cleaning has stopped due to an error")
        sys.exit(1)

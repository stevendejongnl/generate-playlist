import os
import pysftp


# https://ourcodeworld.com/articles/read/813/how-to-access-a-sftp-server-using-pysftp-in-python
from flask import jsonify


def sftp_connection(directory, file_name, handler):
    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None

    with pysftp.Connection(
            host=os.environ.get('SFTP_SERVER'),
            username=os.environ.get('SFTP_USERNAME'),
            password=os.environ.get('SFTP_PASSWORD'),
            cnopts=cnopts,
            log="./sftp.log") as sftp:

        local_file = './{}'.format(file_name)

        sftp.cwd(directory)
        directory_structure = sftp.listdir_attr()

        # Print data
        for attr in directory_structure:
            print(attr.filename, attr)
            if handler == 'put' and attr.filename == file_name:
                try:
                    print(local_file)
                    sftp.put(file_name)
                except IOError:
                    return jsonify(IOError)
                except OSError:
                    return jsonify(OSError)

            if handler == 'get' and attr.filename == file_name:
                try:
                    sftp.get(attr.filename, local_file)
                except IOError:
                    return jsonify(IOError)
                except OSError:
                    return jsonify(OSError)

    return jsonify('Done')

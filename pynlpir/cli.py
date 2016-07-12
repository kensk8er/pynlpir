"""The command-line interface to PyNLPIR."""

import hashlib
import os
import shutil
import tempfile
import zipfile

import rarfile

try:
    from urllib.error import URLError
    from urllib.request import urlretrieve
except ImportError:
    from urllib import urlretrieve
    from urllib2 import URLError

import click

import pynlpir

LICENSE_DIR = 'https://github.com/NLPIR-team/NLPIR/raw/master/License/license%20for%20a%20month'
POSSIBLE_LICENSE_FILES = [
    # it used to be like this, might be back in the future
    'NLPIR-ICTCLAS%E5%88%86%E8%AF%8D%E7%B3%BB%E7%BB%9F%E6%8E%88%E6%9D%83/NLPIR.user',

    # the last time it was downloaded it was like this
    'NLPIR-ICTCLAS%E5%88%86%E8%AF%8D%E7%B3%BB%E7%BB%9F%E6%8E%88%E6%9D%83.zip',

    # latest version was uploaded in this format
    'NLPIR-ICTCLAS%E5%88%86%E8%AF%8D%E7%B3%BB%E7%BB%9F%E6%8E%88%E6%9D%83.rar',
]
POSSIBLE_LICENSE_URLS = ['/'.join([LICENSE_DIR, file_name])
                         for file_name in POSSIBLE_LICENSE_FILES]
DATA_DIR = os.path.join(pynlpir.nlpir.PACKAGE_DIR, 'Data')
LICENSE_FILENAME = 'NLPIR.user'


@click.group(context_settings=dict(help_option_names=['-h', '--help']),
             options_metavar='[<options>]',
             subcommand_metavar='<command> [<args>]')
@click.version_option(pynlpir.__version__, message='%(prog)s %(version)s')
def cli():
    """A simple command-line interface for PyNLPIR."""
    pass


def _is_404(headers):
    """
    Check if the response is 404 or not from headers.

    :param headers: headers returned by urlretrieve function
    :returns bool: return True if it's 404, else False
    """
    for header in headers.headers:
        if header.startswith('Status: 404 Not Found'):
            return True
    else:
        return False


def update_license_file(data_dir):
    """Update NLPIR license file if it is out-of-date or missing.

    :param str data_dir: The NLPIR data directory that houses the license.
    :returns bool: Whether or not an update occurred.

    """
    def get_license_file_path_from_zip(zip_file_path):
        """Return the file_path of the license file in the zip file."""
        with zipfile.ZipFile(gh_license_filename) as zip_file:
            zip_file.extractall(temp_dir)
            for file_path in zip_file.namelist():
                if file_path.endswith(LICENSE_FILENAME):
                    return file_path

        raise Exception('License file not found in the zip file.')

    def extract_zip(zip_file_path):
        """Extract zip file and move the license to the appropriate directory"""
        file_path = get_license_file_path_from_zip(gh_license_filename)

        # extract the zip file
        with zipfile.ZipFile(gh_license_filename) as zip_file:
            zip_file.extractall(temp_dir)

        # move the license file under the temp directory
        os.rename(os.path.join(temp_dir, file_path),
                  os.path.join(temp_dir, gh_license_filename))

    def extract_rar(rar_file_path):
        """Extract rar file and move the license to the appropriate directory"""
        rar_file = rarfile.RarFile(rar_file_path)
        for file_ in rar_file.infolist():
            file_name = file_.filename.replace('\\', os.sep)
            if file_name.endswith(LICENSE_FILENAME):
                # extract the license from the rar file
                rar_file.extract(file_, temp_dir)

                # move the license file under the temp directory
                os.rename(os.path.join(temp_dir, file_name),
                          os.path.join(temp_dir, gh_license_filename))
                return

        raise Exception('License file not found in the rar file.')

    license_file = os.path.join(data_dir, LICENSE_FILENAME)
    temp_dir = tempfile.mkdtemp()
    gh_license_filename = os.path.join(temp_dir, LICENSE_FILENAME)

    try:
        for license_url in POSSIBLE_LICENSE_URLS:
            _, headers = urlretrieve(license_url, gh_license_filename)
            if not _is_404(headers):
                extension = os.path.splitext(license_url)[1]
                break
        else:
            raise URLError('License file not found. File name might have '
                           'changed. Add an appropriate name to '
                           '`POSSIBLE_LICENSE_FILES`.')

    except IOError as e:
        # Python 2 uses the unhelpful IOError for this. Re-raise as the more
        # appropriate URLError.
        raise URLError(e.strerror)

    # Check file extension and extract the license file if necessary
    if extension == '.zip':
        extract_zip(gh_license_filename)
    elif extension == '.rar':
        try:
            extract_rar(gh_license_filename)
        except rarfile.RarUnknownError as exception:
            rarfile.RarUnknownError("{0}\n{1}".format(
                exception,
                'Make sure you have `unrar` installed. On Mac unrar can be '
                'installed by `brew install unrar`.'))

    with open(gh_license_filename, 'rb') as f:
        github_license = f.read()

    try:
        with open(license_file, 'rb') as f:
            current_license = f.read()
    except (IOError, OSError):
        current_license = b''

    github_digest = hashlib.sha256(github_license).hexdigest()
    current_digest = hashlib.sha256(current_license).hexdigest()

    if github_digest == current_digest:
        return False

    shutil.copyfile(gh_license_filename, license_file)
    shutil.rmtree(temp_dir, ignore_errors=True)
    return True


@cli.command(options_metavar='<options>')
@click.option('-d', '--data-dir', help='The NLPIR data directory to use.',
              type=click.Path(exists=True, file_okay=False, writable=True),
              default=DATA_DIR)
def update(data_dir):
    """Update NLPIR license."""
    try:
        license_updated = update_license_file(data_dir)
    except URLError:
        click.secho('Error: unable to fetch newest license.', fg='red')
        exit(1)
    except (IOError, OSError):
        click.secho('Error: unable to move license to data directory.',
                    fg='red')
        exit(1)

    if license_updated:
        click.echo('License updated.')
    else:
        click.echo('Your license is already up-to-date.')

if __name__ == '__main__':
    cli()

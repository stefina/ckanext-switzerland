import unittest
import os
import shutil
import datetime
import boto3
from dateutil.tz import tzutc
from botocore.stub import Stubber
from numpy.testing import assert_array_equal

# The classes to test
# -----------------------------------------------------------------------
from ckanext.switzerland.harvester.s3_storage_adapter import S3StorageAdapter
# -----------------------------------------------------------------------

from ckanext.switzerland.harvester.aws_keys import (
    AWS_SECRET_KEY,
    AWS_ACCESS_KEY,
    AWS_REGION_NAME,
    AWS_BUCKET_NAME
)

LOCAL_PATH = 'localpath'

FILES_AT_ROOT = {
    "Contents": [
        {'Key': 'actual_date_subline_versions_2022-12-20.csv', 'LastModified': datetime.datetime(2022, 12, 20, 2, 20, 1, tzinfo=tzutc(
        )), 'ETag': '"50d4c098d919798c1be34059b1a82f3f"', 'Size': 52299, 'StorageClass': 'STANDARD', 'Owner': {'ID': 'f72bd14b6b6f3869dd203a3ca282a618aaba2ddf8d574a810ff58ac2b578e0a9'}},
        {'Key': 'actual_date_subline_versions_2022-12-20.csv.zip', 'LastModified': datetime.datetime(2022, 12, 20, 2, 20, 1, tzinfo=tzutc(
        )), 'ETag': '"3d0c9020da5748f0a56cb8e13e3cd94a"', 'Size': 11373, 'StorageClass': 'STANDARD', 'Owner': {'ID': 'f72bd14b6b6f3869dd203a3ca282a618aaba2ddf8d574a810ff58ac2b578e0a9'}},
    ]
}

FILES_AT_FOLDER = {
    "Contents": [
        {'Key': 'subline/actual_date_subline_versions_2022-12-19.csv', 'LastModified': datetime.datetime(2022, 12, 20, 2, 20, 1, tzinfo=tzutc(
        )), 'ETag': '"50d4c098d919798c1be34059b1a82f3f"', 'Size': 52299, 'StorageClass': 'STANDARD', 'Owner': {'ID': 'f72bd14b6b6f3869dd203a3ca282a618aaba2ddf8d574a810ff58ac2b578e0a9'}},
        {'Key': 'subline/actual_date_subline_versions_2022-12-19.csv.zip', 'LastModified': datetime.datetime(2022, 12, 20, 2, 20, 1, tzinfo=tzutc(
        )), 'ETag': '"3d0c9020da5748f0a56cb8e13e3cd94a"', 'Size': 11373, 'StorageClass': 'STANDARD', 'Owner': {'ID': 'f72bd14b6b6f3869dd203a3ca282a618aaba2ddf8d574a810ff58ac2b578e0a9'}},
    ]
}

NO_CONTENT = {
}

FOLDER_LIST = {
    'CommonPrefixes': [
        {'Prefix': 'business_organisation/'}, 
        {'Prefix': 'line/'}, 
        {'Prefix': 'opendata_didok/'}, 
        {'Prefix': 'servicepoint_didok/'}, 
        {'Prefix': 'subline/'}, 
        {'Prefix': 'timetable_field_number/'}
    ]
}


class TestS3StorageAdapter(unittest.TestCase):
    temp_folder = '/tmp/s3harvest/tests/'
    remote_folder = '/tests'
    config = {
        LOCAL_PATH: temp_folder,
        AWS_SECRET_KEY: "secret_key",
        AWS_ACCESS_KEY: "access_key",
        AWS_REGION_NAME: "eu-central-1",
        AWS_BUCKET_NAME: AWS_BUCKET_NAME
    }

    @classmethod
    def setup_class(cls):
        pass

    @classmethod
    def teardown_class(cls):
        pass

    def setup(self):
        if os.path.exists(self.temp_folder):
            shutil.rmtree(self.temp_folder, ignore_errors=True)

    def teardown(self):
        if os.path.exists(self.temp_folder):
            shutil.rmtree(self.temp_folder, ignore_errors=True)

    def __stub_aws_client__(self, storage_adapter):
        client = boto3.client('s3')
        storage_adapter._aws_client = client
        stubber = Stubber(client)
        return stubber

    def test_init_when_remote_folder_then_stored_without_trailing_slash(self):
        remote_folder = '/test/'

        storage_adapter = S3StorageAdapter(self.config, remote_folder)

        self.assertEqual('/test', storage_adapter.remote_folder)

    def test_init_without_remote_folder_then_empty(self):
        storage_adapter = S3StorageAdapter(config=self.config)

        self.assertEqual('', storage_adapter.remote_folder)

    def test_init_when_config_then_stored(self):
        storage_adapter = S3StorageAdapter(config=self.config)

        self.assertEqual(self.config, storage_adapter._config)

    def test_init_without_config_then_exception_is_raised(self):
        self.failUnlessRaises(Exception, S3StorageAdapter,
                              None, self.remote_folder)

    def test_init_then_temp_folder_is_created(self):
        folder = self.config[LOCAL_PATH]
        if os.path.exists(folder):
            os.rmdir(folder)

        S3StorageAdapter(self.config, self.remote_folder)

        assert os.path.exists(folder)

    def test_connect_then_session_is_initialized(self):
        storage_adapter = S3StorageAdapter(self.config, self.remote_folder)
        storage_adapter._connect()

        self.assertIsNotNone(storage_adapter._aws_session)

    def test_connect_then_client_is_initialized(self):
        storage_adapter = S3StorageAdapter(self.config, self.remote_folder)
        storage_adapter._connect()

        self.assertIsNotNone(storage_adapter._aws_client)

    def test_cdremote_then_working_directory_is_stored(self):
        storage_adapter = S3StorageAdapter(self.config, self.remote_folder)
        remote_dir = '/remote/'
        storage_adapter.cdremote(remote_dir)

        self.assertEqual('remote', storage_adapter._working_directory)

    def test_cdremote_when_remotedir_is_none_then_working_directory_is_correct(self):
        storage_adapter = S3StorageAdapter(self.config, self.remote_folder)
        storage_adapter.cdremote(None)

        self.assertEqual('', storage_adapter._working_directory)

    def test_with_syntax_then_working_session_is_created(self):
        with S3StorageAdapter(self.config, self.remote_folder) as storage_adapter:
            self.assertEqual('', storage_adapter._working_directory)

    def test_get_top_folder_then_returns_bucket_name(self):
        storage_adapter = S3StorageAdapter(self.config, self.remote_folder)

        self.assertEqual(self.config[AWS_BUCKET_NAME],
                         storage_adapter.get_top_folder())

    def test_get_remote_filelist_at_root_then_returns_correct_list(self):
        storage_adapter = S3StorageAdapter(self.config, self.remote_folder)
        stubber = self.__stub_aws_client__(storage_adapter)
        stubber.add_response("list_objects", FILES_AT_ROOT, {'Bucket': AWS_BUCKET_NAME ,'Prefix': ''})
        stubber.activate()
        expected_files_list = [
            "actual_date_subline_versions_2022-12-20.csv",
            "actual_date_subline_versions_2022-12-20.csv.zip"
        ]

        files_list = storage_adapter.get_remote_filelist()

        assert_array_equal(expected_files_list, files_list)

    def test_get_remote_filelist_at_folder_then_returns_the_correct_names(self):
        storage_adapter = S3StorageAdapter(self.config, self.remote_folder)
        storage_adapter.cdremote('subline')
        stubber = self.__stub_aws_client__(storage_adapter)
        stubber.add_response("list_objects", FILES_AT_FOLDER, {'Bucket': AWS_BUCKET_NAME ,'Prefix': 'subline'})
        stubber.activate()
        expected_files_list = [
            "subline/actual_date_subline_versions_2022-12-19.csv",
            "subline/actual_date_subline_versions_2022-12-19.csv.zip"
        ]

        files_list = storage_adapter.get_remote_filelist()

        assert_array_equal(expected_files_list, files_list)
    
    def test_get_remote_filelist_at_empty_folder_then_returns_empty_list(self):
        storage_adapter = S3StorageAdapter(self.config, self.remote_folder)
        storage_adapter.cdremote('empty')
        stubber = self.__stub_aws_client__(storage_adapter)
        stubber.add_response("list_objects", NO_CONTENT, {'Bucket': AWS_BUCKET_NAME ,'Prefix': 'empty'})
        stubber.activate()
        files_list = storage_adapter.get_remote_filelist()

        assert_array_equal([], files_list)


"""
S3 Storage Adapter
==================

Methods that help with dealing with remote AWS S3 Storage and local folders.
The class is intended to be used with Python's `with` statement, e.g.
`
    with S3StorageAdapter('/remote-base-path/', config) as storage_adapter:
        ...
`
"""
import logging
import boto3
from botocore.exceptions import ClientError
import boto3.session
import os
from storage_adapter_base import StorageAdapterBase
from aws_keys import (
    AWS_SECRET_KEY, 
    AWS_ACCESS_KEY, 
    AWS_REGION_NAME,
    AWS_BUCKET_NAME,
    AWS_RESPONSE_CONTENT,
    AWS_RESPONSE_PREFIXES
)

log = logging.getLogger(__name__)
S3_CONFIG_KEY = 'bucket'
CONFIG_KEYS = [AWS_BUCKET_NAME, AWS_ACCESS_KEY, AWS_REGION_NAME, AWS_SECRET_KEY, "localpath", "remotedirectory"]
class S3StorageAdapter(StorageAdapterBase):
    _aws_session = None
    _aws_client = None
    _working_directory = ''

    def __init__(self, config_resolver, config, remote_folder=''):
        
        super(S3StorageAdapter, self).__init__(config_resolver, config, remote_folder)

        if S3_CONFIG_KEY not in self._config:
            raise KeyError(S3_CONFIG_KEY)

        s3_bucket_key_prefix = 'ckan.s3.' + self._config[S3_CONFIG_KEY]
        
        self.__load_storage_config__(CONFIG_KEYS, s3_bucket_key_prefix)

        self.create_local_dir()

    def __enter__(self):
        self._connect()
        self.cdremote()
        return self

    def __exit__(self, type, value, traceback):
        pass
    
    #TODO: do we want to support other types of credentials configuration => .aws file, with profiles
    def _connect(self):
        self._aws_session = boto3.session.Session(
            aws_access_key_id=self._config[AWS_ACCESS_KEY],
            aws_secret_access_key=self._config[AWS_SECRET_KEY],
            region_name=self._config[AWS_REGION_NAME]
        )

        self._aws_client = self._aws_session.client('s3')
    
    def _disconnect(self):
        # as boto3 is HTTP call based, we don't need to close anything
        pass

    def cdremote(self, remotedir=None):
        # Files are stored flat on AWS. So there is no such command on S3. We just need to keep a ref to a Working Directory
        if remotedir == '/':
            self._working_directory = ''
        elif remotedir:
            self._working_directory = os.path.join(self._working_directory, remotedir.rstrip('/').lstrip('/'))

    def get_top_folder(self):
        # the top folder is basically just the name of the bucket.
        return self._config[AWS_BUCKET_NAME]

    def get_remote_filelist(self, folder=None):
        all_in_folder = self.get_remote_dirlist(folder)
        only_files = filter(lambda name : not name.endswith('/'), all_in_folder)
        return only_files

    def __prepare_for_return__(self, elements, prefix):
        # AWS returns the element with their full name from root, so we need to remove the prefix
        without_prefix = map(lambda file :  file.lstrip(prefix), elements)
        # Of course, we will now have a empty string in the set, let's remove it
        without_root = filter(lambda name : name, without_prefix)
        return without_root

    def __determine_prefix__(self, folder):
        prefix = folder if folder is not None else self._working_directory 
        prefix = prefix + '/' if prefix else ""
        return prefix

    def __clean_aws_response__(self, s3_objects):
        if not s3_objects or AWS_RESPONSE_CONTENT not in s3_objects:
            return []
        
        return map(lambda object : object['Key'], s3_objects[AWS_RESPONSE_CONTENT])


    def get_remote_dirlist(self, folder=None):  
        prefix = self.__determine_prefix__(folder)

        # By fixing the delimiter to '/', we limit the results to the current folder
        s3_objects = self._aws_client.list_objects(Bucket=self._config[AWS_BUCKET_NAME], Prefix=prefix, Delimiter="/")
        
        objects = self.__clean_aws_response__(s3_objects)

        # But the previous call, did not return the folders (because of setting a delimiter), so lets look in the prefixes to add them
        if AWS_RESPONSE_PREFIXES in s3_objects:
            objects.extend(map(lambda object : object['Prefix'], s3_objects[AWS_RESPONSE_PREFIXES]))

        files_and_folder = self.__prepare_for_return__(objects, prefix)

        # AWS always returns sorted items. Usually no need to sort. In this case we need to sort as we aggregated two sources
        files_and_folder.sort()
        
        return files_and_folder
    
    def get_remote_dirlist_all(self, folder=None):
        prefix = self.__determine_prefix__(folder)

        # By fixing the delimiter to '', we list full depth, starting at the prefix depth
        s3_objects = self._aws_client.list_objects(Bucket=self._config[AWS_BUCKET_NAME], Prefix=prefix, Delimiter="")
        
        objects = self.__clean_aws_response__(s3_objects)
        
        return self.__prepare_for_return__(objects, prefix)
    
    def get_modified_date(self, filename, folder=None):
        prefix = self.__determine_prefix__(folder)
        file_full_path = os.path.join(prefix, filename)
        try:
            s3_object = self._aws_client.head_object(Bucket=self._config[AWS_BUCKET_NAME], Key=file_full_path)
            return s3_object['LastModified']
        except ClientError:
            return None
    
    def fetch(self, filename, localpath=None):
        
        object = self._aws_client.get_object(Bucket=self._config[AWS_BUCKET_NAME], Key=filename)
        
        if not localpath:
            localpath = os.path.join(self._config['localpath'], filename)
        
        with open(localpath, 'wb') as binary_file:
            bytes = object['Body'].read()
            binary_file.write(bytes)

        return "226 Transfer complete"

        


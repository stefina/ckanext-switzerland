# encoding: utf-8

'''Tests for the ckanext.switzerland.BaseFTPHarvester.py '''

import unittest

import copy
import json
import os.path
import shutil
import ftplib

import logging
log = logging.getLogger(__name__)

from nose.tools import assert_equal, raises, nottest, with_setup
from mock import patch, Mock
from mock import MagicMock
from mock import PropertyMock

from pylons import config as ckanconf

from simplejson import JSONDecodeError

try:
    from ckan.tests.helpers import reset_db
    from ckan.tests.factories import Organization
except ImportError:
    from ckan.new_tests.helpers import reset_db
    from ckan.new_tests.factories import Organization
from ckan import model
import ckan

from ckanext.harvest.tests.factories import (HarvestSourceObj, HarvestJobObj,
                                             HarvestObjectObj)

# TODO
# from ckanext.harvest.tests.lib import run_harvest

import ckanext.harvest.model as harvest_model

# not needed - mock ftplib instead
# from helpers.mock_ftp_server import MockFTPServer



# The classes to test
# -----------------------------------------------------------------------
from ckanext.switzerland.ftp.FTPHelper import FTPHelper
from ckanext.switzerland.ftp.BaseFTPHarvester import BaseFTPHarvester
# -----------------------------------------------------------------------



class HarvestSource():
    id = 'harvester_id'
    title = 'MyHarvestObject'
    url = '/test/'
    def __init__(self, url=None):
        if url:
            self.url = url
class HarvestJob():
    _sa_instance_state = 'running'
    def __init__(self, id=None, source=None):
        if not id:
            self.id = 'jobid'
        else:
            self.id = id
        if not source:
            self.source = HarvestSource()
        else:
            self.source = source
class HarvestObject():
    id = 'my-harvest-object-id'
    url = 'my-url'
    guid = '1234-5678-6789'
    job__source__owner_org = 'g3298-23hg782-g8743g-348934'
    def __init__(self, guid=None, job=None, content=None, job__source__owner_org=None):
        if guid:
            self.guid = guid
        if content:
            self.content = content
        if job__source__owner_org:
            self.job__source__owner_org = job__source__owner_org
        if not job:
            self.job = HarvestJob()
        else:
            self.job = job
    def get(self, id):
        return self




class TestFTPHelper(unittest.TestCase):

    tmpfolder = '/tmp/ftpharvest/tests/'
    ftp = None

    @classmethod
    def setup_class(cls):

        # config for FTPServer as a tuple (host, port)
        # PORT = 1026 # http://stackoverflow.com/questions/24001147/python-bind-socket-error-errno-13-permission-denied
        # ftpconfig = ('127.0.0.1', PORT) # 990
        # mockuser = {
        #     'username': 'user',
        #     'password': '12345',
        #     'homedir': '.',
        #     'perm': 'elradfmw'
        # }
        # # Start FTP mock server
        # cls.ftp = MockFTPServer(ftpconfig, mockuser)

        pass

    @classmethod
    def teardown_class(cls):
        # close FTP server
        # if cls.ftp:
        #     cls.ftp.teardown()
        #     cls.ftp = None
        pass

    def setup(self):
        pass

    def teardown(self):
        model.repo.rebuild_db()
        # remove the tmp directory
        
        if os.path.exists(self.tmpfolder):
            shutil.rmtree(self.tmpfolder)

    def test_FTPHelper__init__(self):
        """ FTPHelper class correctly stores the ftp configuration from the ckan config """
        remotefolder = '/test/'
        ftph = FTPHelper(remotefolder)

        assert_equal(ftph._config['username'], 'TESTUSER')
        assert_equal(ftph._config['password'], 'TESTPASS')
        assert_equal(ftph._config['host'], 'ftp-secure.sbb.ch')
        assert_equal(ftph._config['port'], 990)
        assert_equal(ftph._config['remotedirectory'], '/')
        assert_equal(ftph._config['localpath'], '/tmp/ftpharvest/tests/')

        assert_equal(ftph.remotefolder, remotefolder.rstrip('/'))

        assert os.path.exists(ftph._config['localpath'])

    def test_get_top_folder(self):
        foldername = "ftp-secure.sbb.ch:990"
        ftph = FTPHelper('/test/')
        assert_equal(foldername, ftph.get_top_folder())

    def test_mkdir_p(self):
        ftph = FTPHelper('/test/')
        ftph._mkdir_p(self.tmpfolder)
        assert os.path.exists(self.tmpfolder)

    def test_create_local_dir(self):
        ftph = FTPHelper('/test/')
        ftph.create_local_dir(self.tmpfolder)
        assert os.path.exists(self.tmpfolder)


    # FTP tests -----------------------------------------------------------

    @patch('ftplib.FTP_TLS', autospec=True)
    def test_connect(self, MockFTP_TLS):

        # get ftplib instance
        mock_ftp = MockFTP_TLS.return_value

        # run
        ftph = FTPHelper('/')
        ftph._connect()

        # constructor was called
        vars = {
            'host': ckanconf.get('ckan.ftp.host', ''),
            'username': ckanconf.get('ckan.ftp.username', ''),
            'password': ckanconf.get('ckan.ftp.password', ''),
        }
        MockFTP_TLS.assert_called_with(vars['host'], vars['username'], vars['password'])

        # login method was called
        # self.assertTrue(mock_ftp.login.called)
        # prot_p method was called
        self.assertTrue(mock_ftp.prot_p.called)

    @patch('ftplib.FTP', autospec=True)
    @patch('ftplib.FTP_TLS', autospec=True)
    def test_connect_sets_ftp_port(self, MockFTP_TLS, MockFTP):
        # run
        ftph = FTPHelper('/')
        ftph._connect()
        # the port was changed by the _connect method
        assert_equal(MockFTP.port, int(ckanconf.get('ckan.ftp.port', False)))

    @patch('ftplib.FTP', autospec=True)
    @patch('ftplib.FTP_TLS', autospec=True)
    def test_disconnect(self, MockFTP_TLS, MockFTP):
        # get ftplib instance
        mock_ftp_tls = MockFTP_TLS.return_value
        # connect
        ftph = FTPHelper('/')
        ftph._connect()
        # disconnect
        ftph._disconnect()
        # quit was called
        self.assertTrue(mock_ftp_tls.quit.called)

    @patch('ftplib.FTP', autospec=True)
    @patch('ftplib.FTP_TLS', autospec=True)
    def test_cdremote(self, MockFTP_TLS, MockFTP):
        # get ftplib instance
        mock_ftp_tls = MockFTP_TLS.return_value
        # connect
        ftph = FTPHelper('/')
        ftph._connect()
        ftph.cdremote('/foo/')
        self.assertTrue(mock_ftp_tls.cwd.called)
        mock_ftp_tls.cwd.assert_called_with('/foo/')

    @patch('ftplib.FTP', autospec=True)
    @patch('ftplib.FTP_TLS', autospec=True)
    def test_cdremote_default_folder(self, MockFTP_TLS, MockFTP):
        # get ftplib instance
        mock_ftp_tls = MockFTP_TLS.return_value
        # connect
        ftph = FTPHelper('/')
        ftph._connect()
        ftph.cdremote()
        self.assertTrue(mock_ftp_tls.cwd.called)
        remotefolder = ckanconf.get('ckan.ftp.remotedirectory', False)
        assert_equal(remotefolder, ftph._config['remotedirectory'])
        mock_ftp_tls.cwd.assert_called_with('')

    @patch('ftplib.FTP', autospec=True)
    @patch('ftplib.FTP_TLS', autospec=True)
    def test_with_ftphelper(self, MockFTP_TLS, MockFTP):
        # get ftplib instance
        mock_ftp_tls = MockFTP_TLS.return_value
        # connect
        with FTPHelper('/hello/') as ftph:
            pass
        self.assertTrue(mock_ftp_tls.cwd.called)
        mock_ftp_tls.cwd.assert_called_with('/hello')
        # class was instantiated with the correct values
        vars = {
            'host': ckanconf.get('ckan.ftp.host', ''),
            'username': ckanconf.get('ckan.ftp.username', ''),
            'password': ckanconf.get('ckan.ftp.password', ''),
        }
        MockFTP_TLS.assert_called_with(vars['host'], vars['username'], vars['password'])
        # prot_p method was called
        self.assertTrue(mock_ftp_tls.prot_p.called)
        # quit was called
        self.assertTrue(mock_ftp_tls.quit.called)

    class FTP_TLS:
        def prot_p(self):
            return
        def nlst(self, folder=None):
            return ['.', '..', 'filea.txt', 'fileb.zip']
        def cwd(self, folder=None):
            return 'cwd into %s' % str(folder)
        def quit(self):
            return 'quitting'
        def retrbinary(self, remotepath, filepointer):
            return [remotepath, filepointer]

    # TODO
    # @patch('ftplib.FTP', autospec=True)
    # @patch('ftplib.FTP_TLS', spec=FTP_TLS)
    # def test_get_remote_dirlist(self, MockFTP_TLS, MockFTP):
    #     # get ftplib instance
    #     mock_ftp_tls = MockFTP_TLS.return_value
    #     # connect
    #     ftph = FTPHelper('/')
    #     ftph._connect()
    #     # get directory listing
    #     dirlist = ftph.get_remote_dirlist('/myfolder/')
    #     # nlst was called
    #     self.assertTrue(mock_ftp_tls.nlst.called)
    #     mock_ftp_tls.nlst.assert_called_with('/myfolder/')
    #     # a filtered directory list was returned
    #     assert_equal(dirlist, ['filea.txt', 'fileb.zip'])

    # TODO
    # @patch('ftplib.FTP', autospec=True)
    # @patch('ftplib.FTP_TLS', spec=FTP_TLS)
    # def test_is_empty_dir(self, MockFTP_TLS, MockFTP):
    #     # get ftplib instance
    #     mock_ftp_tls = MockFTP_TLS.return_value
    #     # connect
    #     ftph = FTPHelper('/')
    #     ftph._connect()
    #     # run
    #     num = ftph.is_empty_dir()
    #     log.debug(num)
    #     self.assertTrue(num > 0)

    # TODO
    # @patch('ftplib.FTP', autospec=True)
    # @patch('ftplib.FTP_TLS', spec=FTP_TLS)
    # def test_fetch(self, MockFTP_TLS, MockFTP):
    #     filename = 'foo.txt'
    #     testfile = '/tmp/foo.txt'
    #     # get ftplib instance
    #     mock_ftp_tls = MockFTP_TLS.return_value        
    #     # connect
    #     with FTPHelper('/') as ftph:
    #         ftph._connect()
    #         # fetch remote file
    #         parameters = ftph.fetch(filename, localpath=testfile)
    #     # tests
    #     log.debug(parameters)
    #     self.assertTrue(mock_ftp_tls.retrbinary.called)
    #     assert_equal(parameters[0], filename)




# =========================================================================

class TestBaseFTPHarvester(unittest.TestCase):

    @classmethod
    def setup_class(cls):
        # Start FTP-alike server we can test harvesting against it
        # mock_ftp.serve()
        # load plugins
        # ckan.plugins.load('ckanext-harvest')
        # ckan.plugins.load('ftpharvester')
        pass

    @classmethod
    def setup(self):
        reset_db()
        # harvest_model.setup()
        pass

    @classmethod
    def teardown_class(cls):
        # unload plugins
        # ckan.plugins.unload('ckanext-harvest')
        # ckan.plugins.unload('ftpharvester')
        pass

    def teardown(self):
        # TODO
        pass

    # -------------------------------------------------------------------------------
    # BEGIN UNIT tests ----------------------------------------------------------------
    # -------------------------------------------------------------------------------

    def test__get_rest_api_offset(self):
        bh = BaseFTPHarvester()
        assert_equal(bh._get_rest_api_offset(), '/api/2/rest')
    def test__get_action_api_offset(self):
        bh = BaseFTPHarvester()
        assert_equal(bh._get_action_api_offset(), '/api/3/action')
    def test__get_search_api_offset(self):
        bh = BaseFTPHarvester()
        assert_equal(bh._get_search_api_offset(), '/api/2/search')

    def test_get_remote_folder(self):
        bh = BaseFTPHarvester()
        assert_equal(bh.get_remote_folder(), '/test/')

    def test_get_local_dirlist(self):
        bh = BaseFTPHarvester()
        dirlist = bh._get_local_dirlist(localpath="./ckanext/switzerland/tests/fixtures/testdir")
        assert_equal(type(dirlist), list)
        assert_equal(len(dirlist), 3)

    def test_set_config(self):
        bh = BaseFTPHarvester()
        bh._set_config('{"myvar":"test"}')
        assert_equal(bh.config['myvar'], "test")

    @raises(JSONDecodeError)
    def test_set_invalid_config(self):
        bh = BaseFTPHarvester()
        bh._set_config('{"myvar":test"}')
        assert_equal(bh.config['myvar'], "test")

    def test_set_invalid_config(self):
        bh = BaseFTPHarvester()
        bh._set_config(None)
        assert_equal(bh.config, {})
        bh._set_config('')
        assert_equal(bh.config, {})

    def test_info_defaults(self):
        bh = BaseFTPHarvester()
        info = bh.info()
        assert_equal(info['name'], 'ckanftpharvest')
        assert_equal(info['title'], 'CKAN FTP ckanftp Harvester')
        assert_equal(info['description'], 'Fetches %s' % '/test/')
        assert_equal(info['form_config_interface'], 'Text')

    def test_info_instantiated(self):
        class MyHarvester(BaseFTPHarvester):
            harvester_name = 'InfoPlus'
            def get_remote_folder(self):
                return '/my/folder/'
        harvester = MyHarvester()
        info = harvester.info()
        assert_equal(info['name'], 'infoplusharvest')
        assert_equal(info['title'], 'CKAN FTP InfoPlus Harvester')
        assert_equal(info['description'], 'Fetches %s' % '/my/folder/')
        assert_equal(info['form_config_interface'], 'Text')

    def test_add_harvester_metadata(self):
        bh = BaseFTPHarvester()
        bh.package_dict_meta = {
            'foo': 'bar',
            'hello': 'world'
        }
        context = {}
        package_dict = bh._add_harvester_metadata({}, context)
        assert package_dict['foo']
        assert package_dict['hello']
        assert_equal(package_dict['foo'], 'bar')
        assert_equal(package_dict['hello'], 'world')

    def test_add_package_tags(self):
        bh = BaseFTPHarvester()
        context = {}
        package_dict = bh._add_package_tags({}, context)
        assert_equal(package_dict['tags'], [])
        assert_equal(package_dict['num_tags'], 0)

        tags = ['a', 'b', 'c']

        bh = BaseFTPHarvester()
        bh.config = {
            'default_tags': tags
        }
        package_dict = bh._add_package_tags({}, context)
        assert_equal(package_dict['tags'], tags)
        assert_equal(package_dict['num_tags'], 3)

    # TODO
    # @nottest
    # def get_action_groups(context, group):
    #     return group
    # @patch('ckan.logic.get_action', spec=get_action_groups)
    # def test_add_package_groups(self, get_action):
    #     context = {}
    #     groups = ['groupA', 'groupB']
    #     bh = BaseFTPHarvester()
    #     bh.config = {
    #         'default_groups': groups
    #     }
    #     package_dict = bh._add_package_groups({}, context)
    #     assert_equal(package_dict['groups'], groups)

    def test_add_package_extras(self):
        package_dict = {
            'id': '123-456-789'
        }
        harvest_object = HarvestObject()
        bh = BaseFTPHarvester()
        extras = {'hello':'world','foo':'bar'}
        # fake a config given in the web interface
        bh.config = {
            'override_extras': True,
            'default_extras': extras
        }
        package_dict = bh._add_package_extras(package_dict, harvest_object)
        assert_equal(package_dict['extras']['foo'], extras['foo'])
        assert_equal(package_dict['extras']['hello'], extras['hello'])

    def test_remove_tmpfolder(self):
        tmpfolder = ''
        bh = BaseFTPHarvester()
        ret = bh.remove_tmpfolder(None)
        assert_equal(ret,  None)
        ret = bh.remove_tmpfolder('')
        assert_equal(ret,  None)

        tmpfolder = '/tmp/test_remove_tmpfolder'
        os.makedirs(tmpfolder, 0777)
        ret = bh.remove_tmpfolder(tmpfolder)
        assert not os.path.exists(tmpfolder)

    # ------------

    def prereqs(self):
        # cleanup before testing
        shutil.rmtree('/tmp/mytestfolder', ignore_errors=True)
    def outro(self):
        # cleanup after testing
        shutil.rmtree('/tmp/mytestfolder', ignore_errors=True)
    class MockFTPHelper:
        def __init__(self, remotefolder):
            self.remotefolder = remotefolder
        def get_remote_dirlist(self):
            return ['hello.txt', 'WorlD.TXT', 'naughty.TMP', 'temporary.tmp']
        def get_top_folder(self):
            return 'mytestfolder'
    class HarvestGatherError():
        message = ''
        def __init__(self, message, job):
            self.message = message
            self.job = job
    @with_setup(prereqs, outro)
    @patch('ftplib.FTP', autospec=True)
    @patch('ftplib.FTP_TLS', autospec=True)
    @patch('ckanext.switzerland.ftp.FTPHelper', spec=MockFTPHelper)
    @patch('ckanext.harvest.model.HarvestObject', autospec=True)
    @patch('ckanext.harvest.model.HarvestGatherError', spec=HarvestGatherError)
    @patch('ckanext.harvest.model.HarvestObjectError', autospec=True)
    def test_gather_stage(self, HarvestObjectError, HarvestGatherError, HarvestObject, MockFTPHelper, FTPLibTLS, FTPLib):
        log.debug(MockFTPHelper)
        # run the test
        myjob = HarvestJob('1234')
        bh = BaseFTPHarvester()
        harvest_object_ids = bh.gather_stage(myjob)
        # check the results
        assert_equal(type(harvest_object_ids), list)
        # there were two files to harvest defined in the MockFTPHelper
        assert_equal(len(harvest_object_ids), 2)




    # def test_fetch_unit(self):
    #     source = HarvestSourceObj(url='http://localhost:%s/' % mock_ckan.PORT)
    #     job = HarvestJobObj(source=source)
    #     harvest_object = HarvestObjectObj(guid=mock_ckan.DATASETS[0]['id'], job=job)
    #     harvester = CKANHarvester()
    #     result = harvester.fetch_stage(harvest_object)
    #     assert_equal(result, True)
    #     assert_equal(
    #         harvest_object.content,
    #         json.dumps(
    #             mock_ckan.convert_dataset_to_restful_form(
    #                 mock_ckan.DATASETS[0])))

    # def test_import_unit(self):
    #     org = Organization()
    #     harvest_object = HarvestObjectObj(
    #         guid=mock_ckan.DATASETS[0]['id'],
    #         content=json.dumps(mock_ckan.convert_dataset_to_restful_form(
    #                            mock_ckan.DATASETS[0])),
    #         job__source__owner_org=org['id'])
    #     harvester = CKANHarvester()
    #     result = harvester.import_stage(harvest_object)
    #     assert_equal(result, True)
    #     assert harvest_object.package_id
    #     dataset = model.Package.get(harvest_object.package_id)
    #     assert_equal(dataset.name, mock_ckan.DATASETS[0]['name'])

    # -------------------------------------------------------------------------------
    # END UNIT tests ----------------------------------------------------------------
    # -------------------------------------------------------------------------------



    # -------------------------------------------------------------------------------
    # BEGIN INTEGRATION tests -------------------------------------------------------
    # -------------------------------------------------------------------------------

    # def test_harvest(self):
    #     results_by_guid = run_harvest(
    #         url='http://localhost:%s/' % mock_ckan.PORT,
    #         harvester=CKANHarvester())

    #     result = results_by_guid['dataset1-id']
    #     assert_equal(result['state'], 'COMPLETE')
    #     assert_equal(result['report_status'], 'added')
    #     assert_equal(result['dataset']['name'], mock_ckan.DATASETS[0]['name'])
    #     assert_equal(result['errors'], [])

    #     result = results_by_guid[mock_ckan.DATASETS[1]['id']]
    #     assert_equal(result['state'], 'COMPLETE')
    #     assert_equal(result['report_status'], 'added')
    #     assert_equal(result['dataset']['name'], mock_ckan.DATASETS[1]['name'])
    #     assert_equal(result['errors'], [])

    # def test_harvest_twice(self):
    #     run_harvest(
    #         url='http://localhost:%s/' % mock_ckan.PORT,
    #         harvester=CKANHarvester())

    #     # change the modified date
    #     datasets = copy.deepcopy(mock_ckan.DATASETS)
    #     datasets[1]['metadata_modified'] = '2050-05-09T22:00:01.486366'
    #     with patch('ckanext.harvest.tests.harvesters.mock_ckan.DATASETS',
    #                datasets):
    #         results_by_guid = run_harvest(
    #             url='http://localhost:%s/' % mock_ckan.PORT,
    #             harvester=CKANHarvester())

    #     # updated the dataset which has revisions
    #     result = results_by_guid[mock_ckan.DATASETS[1]['name']]
    #     assert_equal(result['state'], 'COMPLETE')
    #     assert_equal(result['report_status'], 'updated')
    #     assert_equal(result['dataset']['name'], mock_ckan.DATASETS[1]['name'])
    #     assert_equal(result['errors'], [])

    #     # the other dataset is unchanged and not harvested
    #     assert mock_ckan.DATASETS[1]['name'] not in result

    # def test_harvest_invalid_tag(self):
    #     from nose.plugins.skip import SkipTest; raise SkipTest()
    #     results_by_guid = run_harvest(
    #         url='http://localhost:%s/invalid_tag' % mock_ckan.PORT,
    #         harvester=CKANHarvester())

    #     result = results_by_guid['dataset1-id']
    #     assert_equal(result['state'], 'COMPLETE')
    #     assert_equal(result['report_status'], 'added')
    #     assert_equal(result['dataset']['name'], mock_ckan.DATASETS[0]['name'])

    # def test_exclude_organizations(self):
    #     config = {'organizations_filter_exclude': ['org1-id']}
    #     results_by_guid = run_harvest(
    #         url='http://localhost:%s' % mock_ckan.PORT,
    #         harvester=CKANHarvester(),
    #         config=json.dumps(config))
    #     assert 'dataset1-id' not in results_by_guid
    #     assert mock_ckan.DATASETS[1]['id'] in results_by_guid

    # def test_include_organizations(self):
    #     config = {'organizations_filter_include': ['org1-id']}
    #     results_by_guid = run_harvest(
    #         url='http://localhost:%s' % mock_ckan.PORT,
    #         harvester=CKANHarvester(),
    #         config=json.dumps(config))
    #     assert 'dataset1-id' in results_by_guid
    #     assert mock_ckan.DATASETS[1]['id'] not in results_by_guid

    # def test_harvest_not_modified(self):
    #     run_harvest(
    #         url='http://localhost:%s/' % mock_ckan.PORT,
    #         harvester=CKANHarvester())

    #     results_by_guid = run_harvest(
    #         url='http://localhost:%s/' % mock_ckan.PORT,
    #         harvester=CKANHarvester())

    #     # The metadata_modified was the same for this dataset so the import
    #     # would have returned 'unchanged'
    #     result = results_by_guid[mock_ckan.DATASETS[1]['name']]
    #     assert_equal(result['state'], 'COMPLETE')
    #     assert_equal(result['report_status'], 'not modified')
    #     assert 'dataset' not in result
    #     assert_equal(result['errors'], [])

    # END INTEGRATION tests ---------------------------------------------------------




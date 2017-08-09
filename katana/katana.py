"""
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

"""

import argparse
import glob
import json
import os
import platform
import re
import sys
import inspect
import importlib
import io
import subprocess
import xml.etree.ElementTree as ET
import threading
import xml.etree.ElementTree
from os.path import expanduser
from xml.dom.minidom import parseString

import docstrings
from bottle import route, run, static_file, template, redirect, post, request, \
    response
from docstrings import read_lines, parse_docs, class_defs
from scanfiles import fetch_action_file_names


current_file_dir = os.path.dirname(os.path.realpath(__file__))
# all paths below are relative to current_file_dir
cfg_relpath = './config/config.json'
name_file_relpath = 'name.dat'
datafile_relpath = './config/data.json'
statesfile_relpath = './config/states.json'
newtestcasefile_relpath = './config/newtestcase.xml'
newtestsuitefile_relpath = './config/newtestsuite.xml'
newprojectfile_relpath = './config/newproject.xml'
newdatafile_relpath = './config/newdatafile.xml'
states_relpath = './config/states.json'
newwarhornconfigfile_relpath = './config/newwarhornconfigfile.xml'
newtestdatafile_relpath = './config/newtestdatafile.xml'
deftagsfile_relpath = './config/defaulttags.json'

# compute abs paths
CFGFILE = os.path.normpath((os.path.join(current_file_dir, cfg_relpath)))
NAMEFILE = os.path.normpath((os.path.join(current_file_dir, name_file_relpath)))
DATAFILE = os.path.normpath((os.path.join(current_file_dir, datafile_relpath)))
STATESFILE = os.path.normpath((os.path.join(current_file_dir, statesfile_relpath)))
NEWTESTCASEFILE = os.path.normpath((os.path.join(current_file_dir, newtestcasefile_relpath)))
NEWTESTSUITEFILE = os.path.normpath((os.path.join(current_file_dir, newtestsuitefile_relpath)))
NEWPROJECTFILE = os.path.normpath((os.path.join(current_file_dir, newprojectfile_relpath)))
NEWDATAFILE = os.path.normpath((os.path.join(current_file_dir, newdatafile_relpath)))
STATES = os.path.normpath((os.path.join(current_file_dir, states_relpath)))
NEWWARHORNCONFIGFILE = os.path.normpath((os.path.join(current_file_dir, newwarhornconfigfile_relpath)))
NEWTESTDATAFILE = os.path.normpath((os.path.join(current_file_dir, newtestdatafile_relpath)))
DEFTAGSFILE = os.path.normpath((os.path.join(current_file_dir, deftagsfile_relpath)))
TOOLTIP_DIR = '{0}{1}{2}{1}'.format(current_file_dir, os.sep, 'tooltip')


ROOT = '{0}{1}{2}{1}'.format(current_file_dir, os.sep, 'static') 


@route('/assets/<filename:path>')
def staticfiles(filename):
    return static_file(filename, root=ROOT)


@route('/')
def index():
    redirect('/katana/')


@route('/katana/')
def katana():
    template_lookup = [current_file_dir, "{0}{1}{2}{1}".format(current_file_dir, os.sep, 'views')]
    return template('index', template_lookup=template_lookup)

@route('/readconfig')
def readconfig():
    lines = ""
    with open(CFGFILE, 'r') as f:
        lines = f.read()
    # print 'lines', lines
    cfg = json.loads("".join(lines))
    return cfg

@route('/searchkw', method='POST')
def searchkw():
    """
    This method returns the ActionFile Path of the selected Driver.
    """
    value = parseString("".join(request.body))
    indented_xml = "".join(value.toprettyxml(newl='\n'))
    corrected_xml = remove_extra_newlines_char_xml(indented_xml)
    corrected_xml = corrected_xml
    with open('obj.txt', 'w') as f:
        f.write(corrected_xml)
    tree = ET.parse('obj.txt')
    root = tree.getroot()
    driver_name = root.text
    global gpysrcdir
    driver_file = gpysrcdir + '/ProductDrivers/' + driver_name + ".py"
    actiondir_new = mkactiondirs(driver_file)
    py_files = mkactionpyfiles(actiondir_new)
    return py_files


@route('/parsexmlobj', method='POST')
def parsexmlobj():
    """
    This method fetch the XML object from the Katana UI of Keyword sequencing tool screen.
    And parse it to form a new Wrapper keyword & place it in the user provided file path.
    """
    method_names = []
    arg_name_list = ""
    object_list_new = []
    class_list_new = []
    import_action_list = []
    sample = []
    py_files = ""
    doc_string_value = []
    kw_list_1 = []
    xmlobj = parseString("".join(request.body))
    indented_xml = "".join(xmlobj.toprettyxml(newl='\n'))
    corrected_xml = remove_extra_newlines_char_xml(indented_xml)
    with open('output.txt', 'w') as f:
        f.write(corrected_xml)
    tree = ET.parse('output.txt')
    root = tree.getroot()
    WrapperName = getChildTextbyParentTag('output.txt',
                                          'Details',
                                          'WrapperName')

    ActionFile = getChildTextbyParentTag('output.txt', 'Details', 'ActionFile')
    Description = getChildTextbyParentTag('output.txt', 'Details',
                                          'Description')

    # To check if the user provided wrapper keyword name already exists in action file
    ActionFile = ActionFile.strip()
    with open(ActionFile, 'r') as files:
        for line in files:
            line = line.split()
            if "def" in line:
                next_word = line[line.index("def")+1].split("(")[0]
                method_names.append(next_word)

    if WrapperName in method_names:
        checkval = "yes"
    else:
        checkval = "no"
        Subkeyword = root.find('Subkeyword')
        subkw_list = Subkeyword.findall('Skw')
        count = 0
        for values in subkw_list:
            global gpysrcdir
            subkw_list_attrib = values.attrib
            driver = subkw_list_attrib.get('Driver')
            kw_list = subkw_list_attrib.get('Keyword')
            driver_file = gpysrcdir + '/ProductDrivers/' + driver + ".py"
            actiondir = mkactiondirs(driver_file)
            actions = get_action_dirlist(driver_file)
            pyfiles = mkactionpyfiles(actiondir)
            if len(pyfiles) > 1:
                for action_file in pyfiles:
                    with open(action_file, 'r') as new_file:
                        for line in new_file:
                            line = line.split()
                            if "def" in line:
                                next_word = line[line.index("def")+1].split("(")[0]
                                if next_word == kw_list:
                                    pyfiles = str(action_file).encode('utf-8', 'ignore')

            py_files = str(pyfiles).encode('utf-8', 'ignore')
            (_, file_name) = py_files.rsplit('/', 1)
            path = str(gpysrcdir).encode('utf-8', 'ignore')
            sys.path.append(path)
            file_name = file_name.split('.')[0]
            py_files_1 = py_files.split('/')
            py_files_1 = ('.').join(py_files_1)
            for action in actions:
                if action.strip() in py_files_1:
                    actions_package = action.strip() + "." + file_name
            modules = importlib.import_module(actions_package)
            class_list_new = inspect.getmembers(modules, inspect.isclass)
            for elem in class_list_new:
                if actions_package in str(elem[1]):
                    class_list_new = elem[0]
            import_action_list.append('from ' + action.strip() + "." + file_name + " " +
                                      "import " + class_list_new)
            object_list = class_list_new + "_obj = " + class_list_new + "()"
            object_list_new.append(object_list)
            class_list = (object_list.split('=')[0]).strip()
            Arguments = values.find('Arguments')
            if Arguments is not None:
                argument_list = Arguments.findall('argument')
                len_arg_list = len(argument_list)
                if len(argument_list) == 1:
                    for argument in argument_list:
                        argument_name = argument.get('name')
                        if argument_name is not None:
                            arg_value = argument.get('value')
                            if arg_value is None or arg_value is False:
                                arg_value = argument.text
                            arg_name = argument_name + "=" + "\"" + arg_value + "\""
                            kw_list_1.append("{0}.{1}({2})".format(class_list, kw_list, arg_name))
                            count += 1
                            doc_string_value.append("The keyword {0} in Driver {1} has a defined "
                                                    "arguments {2} You must want to send other "
                                                    "values through data file".format(kw_list,
                                                                                      driver,
                                                                                      arg_name))
                        else:
                            arg_name = ""
                            kw_list_1.append("{0}.{1}({2})".format(class_list, kw_list, arg_name))
                            count += 1
                    doc_string_value.append("The keyword {0} in Driver {1} has a defined "
                                            "arguments {2} You must want to send other values"
                                            " through data file".format(kw_list, driver, arg_name))
                else:
                    for argument in argument_list:
                        argument_name = argument.get('name')
                        if argument_name is not None:
                            arg_value = argument.get('value')
                            if arg_value is None or arg_value is False:
                                arg_value = argument.text
                            arg_list = argument_name + "=" + "\'" + arg_value + "\',"
                            arg_name_list += arg_list
                            count += 1
                    if len_arg_list == count:
                        kw_list_1.append("{0}.{1}({2})".format(class_list, kw_list, arg_name_list))
                    doc_string_value.append("The keyword {0} in Driver {1} has a defined arguments "
                                            "{2} You must want to send other values through data "
                                            "file".format(kw_list, driver, arg_name_list))
                    count = 0
                    arg_name_list = ""
        sum_val = 1
        for _, new in enumerate(doc_string_value):
            sample.append('\n' + "        " + str(sum_val) + ". " + new)
            sample_string = "".join(sample)
            sum_val += 1
            if sum_val > len(subkw_list):
                break
        for line in io.open('kw_seq_template', 'r'):
            with open(ActionFile, 'a+') as f2:
                line = line.replace('$new_line', '\n')
                line = line.replace('$wrapper_kw', WrapperName)
                line = line.replace('$doc_string_values', sample_string)
                if Description is not None:
                    line = line.replace('$wdesc', Description)
                else:
                    line = line.replace('$wdesc', 'Description not provided by the user')
                line = line.replace('$kw_list_1', str(kw_list_1))
                f2.write(line)
        with open(ActionFile, 'a+') as f2:
            for _, vals in enumerate(import_action_list):
                vals = vals.decode('utf-8')
                f2.write('\n' + "        " + vals)
            for _, val in enumerate(object_list_new):
                val = val.decode('utf-8')
                f2.write('\n' + "        " + val)
            for line in io.open('kw_seq_temp', 'r'):
                f2.write('\n' + "    " + line)
        f2.close()
    return checkval


def getChildTextbyParentTag(datafile, pnode, cnode):
    """
    Seraches XML file for the first parent. Finds the child node and returns its text
    datafile = xml file searched
    pnode = parent node
    cnode = child node
    """
    value = False
    tree = ET.parse(datafile)
    root = tree.getroot()
    node = root.find(pnode)
    if node is not None:
        child = node.find(cnode)
        if child is not None:
            value = child.text
            return value
        else:
            return value
    else:
        return value


@route('/readdeftagsfile')
def readdeftagsfile():
    with open(DEFTAGSFILE, 'r') as f:
        lines = f.read()
    data = json.loads("".join(lines))
    return data


@route('/updatedeftags/:tab')
def updatedeftags(tab):
    try:
        with open(DEFTAGSFILE, 'w') as f:
            f.write(tab)
            f.flush()
    except:
        print "Some error occurred while writing to the default tags file"


@route('/readdatafile')
def readdatafile():
    with open(DATAFILE, 'r') as f:
        lines = f.read()
    data = json.loads("".join(lines))
    return data


@route('/readstatesfile')
def readstatesfile():
    with open(STATESFILE, 'r') as f:
        lines = f.read()
    states = json.loads("".join(lines))
    return states




@route('/readtooltip/:tab')
def readtooltip(tab):
    lines = ""
    tooltipfile = TOOLTIP_DIR + tab + '_tooltip.json'
    with open(tooltipfile, 'r') as f:
        lines = f.read()
    # print 'lines', lines
    cfg = json.loads("".join(lines))
    return cfg


@route('/readstates')
def readstates():
    lines = ""
    with open(STATES, 'r') as f:
        lines = f.read()
    # print 'lines', lines
    cfg = json.loads("".join(lines))
    return cfg


@route('/updatestates/:tab')
def updatestates(tab):
    try:
        tab_list = tab.split("%")
        with open(STATES, 'r') as f:
            lines_str = f.read()
        lines_dict = json.loads("".join(lines_str))
        data = lines_dict[tab_list[0]]
        if unicode(tab_list[1]) not in data:
            data.pop()
            data.append(unicode(tab_list[1]))
            data.append(unicode("Add Another"))
        lines_str = json.dumps(lines_dict)
        with open(STATES, 'w'):
            pass
        with open(STATES, 'w') as f:
            f.write(lines_str)
            f.flush()
        return_str = '{"check":"true"}'
        return_dict = json.loads("".join(return_str))
        return return_dict
    except:
        return_str = '{"check":"false"}'
        return_dict = json.loads("".join(return_str))
        return return_dict


def check_path_existance(cfg):
    '''
    A typical config.json entry is:

        "testsuitedir": "/home/vap/labs/fujitsu/integrated/chariot/BaseDirectory/Workspace/Suites",
        "projdir": "/home/vap/labs/fujitsu/integrated/chariot/BaseDirectory/Workspace/Projects",
        "pythonsrcdir": "/home/vap/labs/fujitsu/integrated/chariot/app/raw/python/FrameworkDirectory",
        "xmldir": "/home/vap/labs/fujitsu/integrated/chariot/BaseDirectory/Workspace/Testcases",

    In this function we assert that all paths except the engineer entry in the config.json file is valid.
    '''
    paths = 'testsuitedir projdir pythonsrcdir xmldir pythonpath idfdir testdata warhorn_config'.split()
    op = {
        'status': 'ok',
        'notfounds': []
    }
    nonmandatory = 'testsuitedir projdir xmldir pythonpath idfdir testdata warhorn_config'.split()
    for path in paths:
        print 'path', path
        if path in nonmandatory:
            if cfg[path] != "" and not os.path.exists(cfg[path]):
                op['status'] = 'not-ok'
                op['notfounds'].append(path + ' = ' + cfg[path])
        elif not os.path.isdir(cfg[path]):
            op['status'] = 'not-ok'
            op['notfounds'].append(path + ' = ' + cfg[path])
    return op


# Requires some JSON file as post data
# Dangerous as config file gets edited
@route('/updateconfig', method='POST')
def updateconfig():
    '''
    Attempts to write engineer specified paths to the config file.

    Tries to verify that the path specs actually exist.
    If they do not we flag a complaint listing all the nonextant paths - along with a not-ok flag status.
    else we send back an 'ok' status.
    '''
    lines, httpstatus, op = "", 200, {}
    lines = json.dumps(request.json, indent=2)
    cfg = json.loads(lines)
    if cfg is None:
        with open(CFGFILE, 'r') as f:
            cfg = json.load(f)
            lines = json.dumps(cfg, indent=2)
    op = check_path_existance(cfg)
    if (op['status'] == 'ok'):
        with open(CFGFILE, 'w') as f:
            f.write(lines)
    else:
        httpstatus = 400
    print 'op', op
    print 'updateconfig.lines', lines
    print 'httpstatus', httpstatus
    response.status = httpstatus
    return json.dumps(op)

@route('/updateconfigfromtab/:dir/:data', method="POST")
def updateconfigfromtab(dir, data):
    output = {"updated": "yes"}
    try:
        path_list = data.split("$sep$")
        path = path_list[0]
        for i in range(1, len(path_list)):
            path += os.sep + path_list[i]
        print path
        with open(CFGFILE, 'r') as f:
            lines = f.read()
        cfg = json.loads("".join(lines))
        cfg[dir] = path
        print cfg
        with open(CFGFILE, 'w') as f:
            f.write(json.dumps(cfg, indent=2))
    except Exception, e:
        print e
        output = {"updated": "no"}
    return output



@route('/checkfilepath/:data')
def checkfilepath(data):
    '''
    '''
    output = {"exists": "no"}
    path_list = data.split("$sep$")
    path = path_list[0]
    for i in range(1, len(path_list)):
        path += os.sep + path_list[i]
    print path
    if os.path.exists(path):
        output["exists"] = "yes"

    return output

@route('/populatepaths/:data')
def populatepaths(data):
    path_list = data.split("$sep$")
    path = path_list[0]
    for i in range(1, len(path_list)):
        path += os.sep + path_list[i]
    output = {}
    dirs = {"xmldir": "Testcases",
            "testsuitedir": "Suites",
            "projdir": "Projects",
            "idfdir": "Data",
            "testdata": "Config_files"}
    for key, value in dirs.iteritems():
        if os.path.exists(os.path.join(path, "Warriorspace", value)):
            output[key] = os.path.join(path, "Warriorspace", value)
        else:
            output[key] = ""
    print output
    return output


@post('/writeconfig')
def writeconfig():
    '''Write the map cfg to 'CFGFILE' file.'''
    lines = json.dumps(request.json, indent=2)
    with open(CFGFILE, 'w') as f:
        f.write(lines)
    return lines


@route('/readuser')
def readuser():
    lines = ""
    with open(CFGFILE, 'r') as f:
        lines = f.read()
    print 'lines', lines
    usr = json.loads("".join(lines));
    return usr


############################## Docstring handling start ############################
def pathname(dir):  # changed
    print "i'm handling dir here \n\n"
    print "\n >>>> dir: >>", dir
    print dir[-1]
    print "\n\n\n"
    if dir[-1] != os.sep:
        dir += os.sep
    return dir


def namecase(s):
    return s[0].upper() + s[1:].lower()


gpysrcdir = ''


def mkactiondirs(driverpath):  # changed
    '''Given a directory name `drivername`, return its action python file name.'''
    # FrameworkDirectory/ used to be the prefix in the directory name.
    actions_dirpath_list = []
    actions_package_list = get_action_dirlist(driverpath)
    if len(actions_package_list) == 0:
        print "the driver {0} does not import any actions package or import format is wrong".format(
            os.path.basename(driverpath))
    # print "action package list in mkactions dir", actions_package_list
    # print type(actions_package_list)

    elif len(actions_package_list) > 0:
        for package in actions_package_list:
            try:
                print package
                package = package.replace(' ', '')
                pkg = re.sub('[\n\t' '\\\]', '', package)
                print pkg
                print package
                if pkg == 'Actions':
                    actions_dirpath = gpysrcdir + os.sep + 'Actions'
                elif pkg.startswith('Actions.'):
                    path = pkg.replace('.', os.sep)
                    actions_dirpath = gpysrcdir + os.sep + path
                else:
                    path = pkg.replace('.', os.sep)
                    actions_dirpath = gpysrcdir + os.sep + 'Actions' + os.sep + path
                    print actions_dirpath
                if os.path.isdir(actions_dirpath):
                    actions_dirpath_list.append(actions_dirpath)
                else:
                    print "the actions package {0} does not exist or the location is not compatible with warrior framework:".format(
                        actions_dirpath)
            except Exception, e:
                print str(e)
    return actions_dirpath_list


def get_action_dirlist(driverpath):  # changed
    """ Get the list of action directories """
    actions_package_list = []
    try:
        if os.path.isfile(driverpath):
            '''
            fobj = open(driverpath, 'r')
            lines = fobj.readlines()
            '''
            lines = []
            with open(driverpath, 'r') as fobj:
                lines = fobj.readlines()
            lines_as_string = ''.join(lines)
            search_string = re.compile('package_list.*=.*\]',
                                       re.DOTALL | re.MULTILINE)
            match = re.search(search_string, lines_as_string)

            if match:
                match_string = match.group()
                # print match_string
                actions_package_list = match_string.split('[')[1].split(']')[
                    0].split(',')
                print "\n action package list: ", actions_package_list
                # for line in lines:
                # if re.search(search, line):
                # print "package_list found"
                # print line
                # actions_package_list = line.split('[')[1].split(']')[0].split(',')
                # print "\n action package list: ", actions_package_list
            return actions_package_list
        else:
            print "file {0} does not exist".format(driverpath)
            return actions_package_list
    except Exception, e:
        print str(e)
    return actions_package_list


def mkactionpyfiles(dirlist):  # changed
    '''Find .py files in given directory.'''
    # print "dirlist for action py file s=>>>>>>>>>>>>>>", dirlist
    final_py_list = []
    try:
        for dir in dirlist:
            pyfile_list = glob.glob(dir + os.sep + '*.py')
            # print "pyfile list ---->", pyfile_list
            for pyfile in pyfile_list:
                nameonly = os.path.basename(pyfile)
                if nameonly.startswith("__init__"):
                    pyfile_list.remove(pyfile)
            final_py_list.extend(pyfile_list)
        return final_py_list
    except Exception, e:
        print str(e)
        return final_py_list


def fetchpath(keyname):
    config = readconfig()
    # print 'fetchpath, config:', config
    return pathname(config['cfg'][keyname])


def fetch_comments(sa):
    '''From the tuple array, made of (drivername, array_of_filenames),
    build the comments data structure.'''
    res = {}
    for a in sa:
        comments = []
        for f in a[1]:
            comments.append(docstrings.parse_py_file(f))
        res[a[0]] = comments
    return res


def py_file_details():  # changed
    global gpysrcdir
    print gpysrcdir
    cfg = readconfig()
    print cfg
    # gpysrcdir = fetchpath('pythonsrcdir')
    # gpysrcdir = pathname(cfg['pythonsrcdir'])
    gpysrcdir = cfg['pythonsrcdir']
    print ">>> source directory:", gpysrcdir

    pyfiles_list = glob.glob(
        gpysrcdir + os.sep + 'ProductDrivers' + os.sep + '*.py')
    pyfiles = []
    for fl in pyfiles_list:
        print fl
        if os.path.isfile(fl):
            print "is a file:", fl
            if os.path.basename(fl) != '__init__.py':
                print "not init hence accepting"
                pyfiles.append(fl)
        else:
            print "not a file", fl

    driver_nameonly = map(lambda f: os.path.basename(f), pyfiles)
    drivers = sorted([df[:df.find('.py')] for df in driver_nameonly])
    drivers_fpath = sorted([df for df in pyfiles])
    # print 'drivers', json.dumps(drivers)
    # print 'drivers_fpath', json.dumps(drivers_fpath)
    print "\n*****pyfiles : \n\n", pyfiles
    print "\n***** drivers nameonly: \n\n", driver_nameonly
    print "\n***** drivers: \n\n", drivers
    print "\n***** drivers fullpath: \n\n", drivers_fpath

    # actiondirs = []
    # for path in drivers_fpath:
    #     for directory in mkactiondirs(path):
    #         actiondirs.append(directory)
    actiondirs = map(mkactiondirs, drivers_fpath)
    print "\n\n drivers: \n\n", json.dumps(drivers_fpath, indent=2)
    print '\n\nactiondirs: \n\n', json.dumps(actiondirs, indent=2)

    actionpyfiles = map(mkactionpyfiles, actiondirs)
    drivercomments = fetch_comments(zip(drivers, actionpyfiles))
    # print 'driver:docs\n', json.dumps(drivercomments, indent=2)
    return drivercomments


###################################Docstring handling end####################################################

@route('/fetchxml')
def fetchxml():
    lines = ""
    with open('./xml/test-case-n1.xml', 'r') as f:
        lines = f.read()
    print 'lines', lines
    return "".join(lines);


@route('/engineer')
def fetchengineer():
    cfg = readconfig()
    engineer = cfg['engineer']
    final_json = {"engineer": engineer}
    return json.dumps(final_json)


@route('/testcasefilenames/:directory')
def testcasefiles(directory):
    if directory == "none":
        directory = None
    onlyfiles = getSubFiles('xmldir', directory)
    return onlyfiles


@route('/testcasefoldernames/:directory')
def testcasefiles(directory):
    if directory == "none":
        directory = None
    onlyfolders = getSubFolders('xmldir', directory)
    return onlyfolders


@route('/testcase/:filename/:subdirs')
def testcasefile(filename, subdirs):
    if subdirs == "none":
        subdirs = None
    content = getXMLFileContent('xmldir', NEWTESTCASEFILE, filename, subdirs)
    return content


@route('/warhornconfigfile/:filename/:subdirs')
def warhornconfigfile(filename, subdirs):
    if subdirs == "none":
        subdirs = None
    content = getXMLFileContent('warhorn_config', NEWWARHORNCONFIGFILE,
                                filename, subdirs)
    return content


@route('/testDatafile/:filename/:subdirs')
def testdatafile(filename, subdirs):
    if subdirs == "none":
        subdirs = None
    content = getXMLFileContent('testdata', NEWTESTDATAFILE, filename, subdirs)
    return content


def getXMLFileContent(identifier, filetype, filename, subdirs=None):
    dir_path = getDirectoryPath(subdirs)
    cfg = readconfig()
    if filename == '__new__':
        with open(filetype, 'r') as f:
            xmlfilecontent = f.read()
    else:
        with open(cfg[identifier] + dir_path + os.sep + filename, 'r') as f:
            xmlfilecontent = f.read()
    if identifier == "xmldir":
        res = {'xml': xmlfilecontent,
               'pycmts': py_file_details(),
               'engineer': cfg['engineer'],
               'filename': filename}
    else:
        res = {'xml': xmlfilecontent, 'filename': filename}
    print xmlfilecontent
    return json.dumps(res)


@route('/datafile/:filename/:subdirs')
def datafile(filename, subdirs):
    print subdirs
    if subdirs == "none":
        subdirs = None
    content = getXMLFileContent('idfdir', DATAFILE, filename, subdirs)
    return content


# @route('/testcase/:filename')
# def testcasefile(filename):
#     lines = ""
#     cfg = readconfig()
#     with open(cfg['xmldir'] + "/" + filename) as f:
#         lines = f.read()
#     print 'lines', lines
#     return "".join(lines);


@route('/fetchdocstrings')
def fetchdocstrings():
    # fetch_action_file_names('D:/fujitsu_vijay/app/raw/python')
    json_data = []
    cfg = readconfig()
    files = cfg['pythonsrcdir'] + '/python'
    print files
    sa = fetch_action_file_names(files, 'action', 'all')
    for k, v in sa.iteritems():
        for i in v:
            pyfile = i
            lines = read_lines(pyfile)
            defs = class_defs(lines, pyfile)
            parse_docs(lines, defs, pyfile)
            json_data.append(defs)
    return json.dumps(json_data, indent=2)


@route('/querydirectory', method='POST')
def querydirectory():
    request_json = json.dumps(request.json)
    print 'querydirectory: request_json:', request_json
    request_json = json.loads(request_json)
    directory = request_json['directory']
    if directory == "":
        directory = expanduser("~")
    try:
        contents = os.listdir(directory)
        print contents
        files = []
        folders = []
        for i in contents:
            if os.path.isfile(directory + '/' + i):
                files.append(i)
            elif os.path.isdir(directory + '/' + i):
                folders.append(i)
            else:
                print 'not a file or folder %' % i
        json_data = {
            "files": files,
            "folders": folders
        }
        final_json = {
            "data": json_data,
            "status": "success",
            "errorstring": "",
            "currentdirectory": directory

        }
    except OSError as errorInfo:

        final_json = {"data": {},
                      "status": "fail",
                      "errorstring": str(errorInfo),
                      "currentdirectory": directory
                      }

    print 'FINAL JSON'
    print json.dumps(final_json)
    return json.dumps(final_json)


# function to find the parent directory of the given directory.
# If the given directory name is in directory/filename.extension format, the output will be directory.
# If the user has given wrong directory name also this will find the parent directory

@route('/gotoparentdirectory', method='POST')
def gotoparentdirectory():
    request_json = json.dumps(request.json)
    request_json = json.loads(request_json)
    directory = request_json['directory']
    if directory == "":
        directory = expanduser("~")

    parent_dir = os.path.abspath(os.path.join(directory, os.pardir))
    print parent_dir
    try:
        contents = os.listdir(parent_dir)
        print contents
        files = []
        folders = []
        for i in contents:
            if os.path.isfile(parent_dir + '/' + i):
                files.append(i)
            elif os.path.isdir(parent_dir + '/' + i):
                folders.append(i)
            else:
                print 'not a file or folder %' % i
        json_data = {
            "files": files,
            "folders": folders
        }
        final_json = {
            "data": json_data,
            "status": "success",
            "errorstring": "",
            "currentdirectory": parent_dir

        }
    except OSError as errorInfo:

        final_json = {"data": {},
                      "status": "fail",
                      "errorstring": str(errorInfo),
                      "currentdirectory": parent_dir
                      }

    print 'FINAL JSON'
    print json.dumps(final_json)
    return json.dumps(final_json)


@route('/authenticateuser', method='POST')
def authenticateuser():
    usr = readuser()
    print usr

    request_json = json.dumps(request.json)
    print json.dumps(request_json)
    request_json = json.loads(request_json)
    request_username = request_json['username']
    request_password = request_json['password']
    flag = 0
    flagUnm = 0
    flagPswd = 0

    for i in range(len(usr)):
        stored_username = usr[i]['name']
        stored_password = usr[i]['password']
        role = usr[i]['role']
        email = usr[i]['email']
        if request_username == stored_username:
            flagUnm = 1
        if request_password == stored_password:
            flagPswd = 1
        if flagUnm == 1 and flagPswd == 1:
            json_data = {
                "username": request_username,
                "role": role,
                "email": email
            }

            final_json = {
                "status": "success",
                "data": json_data,
                "errorInfo": ""
            }

            break

    if flagUnm == 0 and flagPswd == 0:
        final_json = {
            "status": "fail",
            "data": {},
            "errorInfo": "Incorrect Username and Password"
        }
    elif flagPswd == 0:
        final_json = {
            "status": "fail",
            "data": {},
            "errorInfo": "Incorrect Password"
        }
    elif flagUnm == 0:
        final_json = {
            "status": "fail",
            "data": {},
            "errorInfo": "Incorrect Username"
        }

    print json.dumps(final_json)
    return json.dumps(final_json)


@route('/executecommand', method='POST')
def executecommand():
    request_json = json.dumps(request.json)
    print request_json
    # request_json={"command":"rename","arguments":["new.txt","old.txt"]}


    request_json = json.loads(request_json)

    request_command = request_json['command']
    request_argument = request_json['arguments']
    request_mode = request_json['mode']
    argument_string = ""
    for i in request_argument:
        argument_string = argument_string + " " + i
        print argument_string
    try:
        output = ""
        command_to_execute = request_command + " " + argument_string
        print 'COMMAND TO BE EXECUTED IS %s' % command_to_execute
        if request_mode == 'blocking':
            output = executecommandfunction(command_to_execute)
        elif request_mode == 'nonblocking':
            executecommandthread = threading.Thread(
                target=executecommandfunction, args=(command_to_execute,))
            executecommandthread.start()
        # output=subprocess.Popen(request_command+" "+argument_string,shell=True, stderr=subprocess.PIPE).stderr.read()

        if output == "":
            json_data = {
                "status": "success",
                "errorInfo": {}
            }
        elif output != "":
            json_data = {
                "status": "fail",
                "errorInfo": output
            }
    except Exception as errorInfo:
        print errorInfo
    print json.dumps(json_data)
    return json.dumps(json_data)


def executecommandfunction(command_to_execute):
    output = subprocess.Popen(command_to_execute, shell=True,
                              stderr=subprocess.PIPE).stderr.read()
    return output


@route('/getdrivernames')
def getdrivernames():
    drivers = []
    cfg = readconfig()
    files = cfg['pythonsrcdir']
    print files
    sa = fetch_action_file_names(files, 'driver', 'none')
    print 'PRINTING SA'

    for k, v in sa.iteritems():
        for i in v:
            files = i.replace("\\", '/')
            filename = files.rsplit('/', 1)
            fileName = filename[1].rpartition('_')[0]
            drivers.append(fileName.title())
    json_data = {
        "drivers": drivers
    }
    print json.dumps(json_data)
    return json.dumps(json_data)


@route('/getactionOld', method='POST')
def getactionOld():
    json_data = []
    request_json = json.dumps(request.json)
    print request_json
    request_json = json.loads(request_json)

    request_action = request_json['action']
    print 'action name %s' % request_action
    cfg = readconfig()
    files = cfg['pythonsrcdir'] + '/python'
    print files
    sa = fetch_action_file_names(files, 'action', request_action)

    for k, v in sa.iteritems():
        for i in v:
            pyfile = i
            lines = read_lines(pyfile)
            defs = class_defs(lines, pyfile)
            parse_docs(lines, defs, pyfile)
            json_data.append(defs)
    print json.dumps(json_data, indent=2)
    return json.dumps(json_data, indent=2)


@route('/getaction', method='POST')
def getaction():
    json_data = []
    request_json = json.dumps(request.json)
    print request_json
    request_json = json.loads(request_json)

    request_action = request_json['action']
    print 'action name %s' % request_action

    cfg = readconfig()
    files = cfg['pythonsrcdir']
    print 'pythonsrcdir: ' + files

    driverfile = files + '/ProductDrivers/' + request_action.lower() + '_driver.py'
    print 'driverfile %s' % driverfile
    packagelist = findPackageListNew(driverfile)
    for i in packagelist:
        action_name = i.replace('Actions.', '')
        action_name = action_name.replace('Actions', '')
        action_name = action_name.lstrip()
        print action_name
        sa = fetch_action_file_names(files, 'action', action_name)

        # sa=fetch_action_file_names(files,'action',request_action)

        for k, v in sa.iteritems():
            for i in v:
                pyfile = i
                lines = read_lines(pyfile)
                defs = class_defs(lines, pyfile)
                parse_docs(lines, defs, pyfile)
                json_data.append(defs)
    print json.dumps(json_data, indent=2)
    return json.dumps(json_data, indent=2)


def findPackageList(driverfile):
    lines = []
    packagelist = []
    with open(driverfile, 'r') as f:
        lines = f.readlines()
    lines = map(lambda r: r.strip(), lines)
    print lines
    for i in lines:
        if i.startswith('package_list '):
            packages = ((i.split('['))[1].split(']')[0])
            print packages
            break

    packagelist = packages.split(',')
    print packagelist
    return packagelist


def findPackageListNew(driverfile):
    lines = []
    packagelist = []
    packagestring = ""
    flagStarted = 0
    packages = ''

    with open(driverfile, 'r') as f:
        lines = f.readlines()
    lines = map(lambda r: r.strip(), lines)
    print lines
    for i in lines:
        if i.startswith('package_list '):
            if '[' in i and ']' in i:
                packages = ((i.split('['))[1].split(']')[0])
                print packages
                break
            elif '[' in i and ']' not in i:
                flagStarted = 1
                packagestring = packagestring + i
                print 'packagestring %s' % packagestring
                continue
        if flagStarted == 1 and ']' in i:
            packagestring = packagestring + i
            print 'packagestring 1111 %s' % packagestring
            flagStarted = 2
            packages = ((packagestring.split('['))[1].split(']')[0])
            print packages
            break
        elif flagStarted == 1 and ']' not in i:
            packagestring = packagestring + i
            print 'packagestring 22222 %s' % packagestring

    packagelist = packages.split(',')
    print packagelist
    return packagelist


@route('/checkfileexist/:filename/:filetype')
def checkfileexist(filename, filetype):
    output = checkExistenceOfFile(filename, filetype)
    return output


@route('/checkfileexistwithsubdir/:filename/:filetype/:subdirs')
def checkfileexistwithsubdir(filename, filetype, subdirs):
    if subdirs == "none":
        subdirs = None
    output = checkExistenceOfFile(filename, filetype, subdirs)
    return output


def checkExistenceOfFile(filename, filetype, subdirs=None):
    dir_path = getDirectoryPath(subdirs)

    folder = {
        "testcase": "xmldir",
        "suite": "testsuitedir",
        "project": "projdir",
        "warhornconfigfile": "warhorn_config",
        "testdatafile": "testdata",
        "datafile": "idfdir"
    }

    cfg = readconfig()
    filedir = cfg[folder[filetype]]

    completeFilePath = filedir + dir_path + os.sep + filename

    if os.path.isfile(completeFilePath):
        json_data = {
            "response": "yes"
        }
    else:
        json_data = {
            "response": "no"
        }

    print json.dumps(json_data, indent=2)
    return json.dumps(json_data, indent=2)


# Suite Handling#####################################################################################
@route('/testsuitefilenames/:directory')
def testsuitefiles(directory):
    if directory == "none":
        directory = None
    onlyfiles = getSubFiles('testsuitedir', directory)
    return onlyfiles


@route('/testsuitefoldernames/:directory')
def testsuitefolder(directory):
    if directory == "none":
        directory = None
    onlyfolders = getSubFolders('testsuitedir', directory)
    return onlyfolders


@route('/testsuite/:filename/:subdirs')
def testsuitefile(filename, subdirs):
    if subdirs == "none":
        subdirs = None
    content = getXMLFileContent('testsuitedir', NEWTESTSUITEFILE, filename, subdirs)
    return content


@route('/savetestcase/:filename/:subdirs', method='POST')
def savetestcase(filename, subdirs):
    output = saveFile(filename, subdirs, "xmldir")
    return output


@route('/savetestsuite/:filename/:subdirs', method='POST')
def saveTestsuite(filename, subdirs):
    output = saveFile(filename, subdirs, "testsuitedir")
    return output


@route('/savedatafile/:filename/:subdirs', method='POST')
def saveDataFile(filename, subdirs):
    output = saveFile(filename, subdirs, "idfdir")
    return output


# Project Handling #

@route('/projectfilenames/:directory')
def projectfiles(directory):
    if directory == "none":
        directory = None
    onlyfiles = getSubFiles('projdir', directory)
    return onlyfiles


@route('/projectfoldernames/:directory')
def projectfolders(directory):
    if directory == "none":
        directory = None
    onlyfolders = getSubFolders('projdir', directory)
    return onlyfolders


@route('/datafoldernames/:directory')
def testdatafoldernames(directory):
    if directory == "none":
        directory = None
    onlyfolders = getSubFolders('idfdir', directory)
    return onlyfolders


@route('/datafilenames/:directory')
def datafiles(directory):
    if directory == "none":
        directory = None
    onlyfiles = getSubFiles('idfdir', directory)
    return onlyfiles


@route('/project/:filename/:subdirs')
def projectfile(filename, subdirs):
    if subdirs == "none":
        subdirs = None
    content = getXMLFileContent('projdir', NEWPROJECTFILE, filename, subdirs)
    return content


@route('/saveproject/:filename/:subdirs', method='POST')
def saveproject(filename, subdirs):
    output = saveFile(filename, subdirs, "projdir")
    return output


@route('/savewarhornconfigfile/:filename/:subdirs', method='POST')
def saveWarhornConfigFile(filename, subdirs):
    output = saveFile(filename, subdirs, "warhorn_config")
    return output


@route('/savetestdatafile/:filename/:subdirs', method='POST')
def saveTestDataFile(filename, subdirs):
    output = saveFile(filename, subdirs, "testdata")
    return output


def saveFile(filename, subdirs, filetype):
    dir_path = getDirectoryPath(subdirs)
    xmldom = parseString("".join(request.body))
    if filename != "":
        cfg = readconfig()
        xmldir = cfg[filetype]
        indented_xml = "".join(xmldom.toprettyxml(newl='\n'))
        corrected_xml = remove_extra_newlines_char_xml(indented_xml)
        print corrected_xml
        with open(xmldir + dir_path + os.sep + filename, "w") as f:
            f.write(corrected_xml)
        output = {"success": True,
                  "path": filename}
    else:
        output = {"success": False,
                  "error": "Save called without a filename or content!"}

    return output


def remove_extra_newlines_char_xml(indented_xml):
    re_correction = re.compile(r'((?<=>)(\n[ ]*)(?=[^< ]))|(?<=[^> ])(\n[ ]*)(?=<)')
    corrected_xml = re.sub(re_correction, '', indented_xml.expandtabs())
    return corrected_xml


def getDirectoryPath(subdirs):
    dir_path = ""
    if subdirs != "" and subdirs is not None and subdirs != "none":
        dir_list = subdirs.split(',')
        for dirs in dir_list:
            if dir_path == "":
                dir_path = os.sep + dirs
            else:
                dir_path = dir_path + os.sep + dirs
    return dir_path


@route('/warhornconfigfoldernames/:directory')
def testdatafoldernames(directory):
    if directory == "none":
        directory = None
    onlyfolders = getSubFolders('warhorn_config', directory)
    return onlyfolders


@route('/warhornconfigfilenames/:directory')
def warhornconfigfiles(directory):
    if directory == "none":
        directory = None
    onlyfiles = getSubFiles('warhorn_config', directory)
    return onlyfiles


@route('/testdatafilenames/:directory')
def testdatafiles(directory):
    if directory == "none":
        directory = None
    onlyfiles = getSubFiles('testdata', directory)
    return onlyfiles


@route('/testdatafoldernames/:directory')
def testdatafoldernames(directory):
    if directory == "none":
        directory = None
    onlyfolders = getSubFolders('testdata', directory)
    return onlyfolders


def getSubFolders(identifier, directory=None):
    cfg = readconfig()
    folders = []
    dir_path = getDirectoryPath(directory)
    onlyfolders = []
    if cfg[identifier].strip() != "":
        temp = glob.glob(cfg[identifier] + dir_path + "/*")
        for folder in temp:
            if os.path.isdir(folder):
                folders.append(folder)
        folders = [f.replace("\\", '/') for f in folders]
        onlyfolders = map(lambda f: f.rpartition('/')[2], folders)
        print 'only-folders', onlyfolders
    return json.dumps(onlyfolders)


def getSubFiles(identifier, directory=None):
    cfg = readconfig()
    dir_path = getDirectoryPath(directory)
    onlyfiles = []
    if cfg[identifier].strip() != "":
        files = glob.glob(cfg[identifier] + dir_path + "/*.xml")
        files = [f.replace("\\", '/') for f in files]
        onlyfiles = map(lambda f: f.rpartition('/')[2], files)
        print 'only-files', onlyfiles
    return json.dumps(onlyfiles)


# @route('/showdescription/', method='POST')
@route('/showdescription', method='GET')
def showdescription():
    desc_content = []
    description_val = ""
    desctype = request.GET.get("desctype", '').strip().lower()
    print 'desctype', desctype
    '''
    if (desctype == "sequential"):
        read_config = open("sequential_description.dat")
        description_val = (read_config.read()).strip()
    elif(desctype == "parallel"):
        read_config = open("parallel_description.dat")
        description_val = (read_config.read()).strip()
    else:
        read_config = open("performance_description.dat")
        description_val = (read_config.read()).strip()
    description_val = description_val.replace("\n", " ")
    desc_content.append({'description': description_val})
    return json.dumps(desc_content)
    '''
    filename = 'execution_description.dat'
    if desctype == 'sequential':
        filename = 'execution_description.dat'

    elif desctype == 'run selected files in sequence':
        filename = 'sequential_description.dat'

    elif desctype == 'run keywords in parallel':
        filename = 'parallel_description.dat'

    elif desctype == 'performance test mode':
        filename = 'performance_description.dat'

    description_val = ''
    with open(filename, 'r') as file:
        description_val = file.read()
    description_val = description_val.replace("\n", ' ').strip()
    print 'description_val', description_val
    desc_content.append({'description': description_val})
    return json.dumps(desc_content)


'''
-----------------------------------
This function should not be a POST.
-----------------------------------
@route('/search/', method='POST')
def search():
    print 'In search/'
    file_paths = []
    dirname = request.forms.get("dirname")
    dirname = dirname.strip() + os.sep
    print 'dirname', dirname
    for root, directories, files in os.walk(dirname):
        for filename in files:
            if filename.endswith(".xml"):
                print filename
                filepath = os.path.join(root, filename)
                file_paths.append({'filename': filepath})  # Add it to the list.iles = [ f.replace("\\", '/') for f in files ]
    return json.dumps(file_paths)
'''


@route('/search', method='GET')
def search():
    file_paths = []
    # In case there's no dirname key, we arrange to return 0 length file list array.
    dirname = request.GET.get("dirname", 'no-dir-name')
    dirname = dirname.strip() + os.sep
    print 'dirname', dirname
    for root, directories, files in os.walk(dirname):
        for filename in files:
            if filename.endswith(".xml"):
                print filename
                filepath = os.path.join(root, filename)
                file_paths.append({
                                      'filename': filepath})  # Add it to the list.iles = [ f.replace("\\", '/') for f in files ]
    return json.dumps(file_paths)


@route('/execute/', method='POST')
def execute():
    command_response = []
    filenames = request.forms.get("filenames")
    filenames = filenames.strip()
    exectype = request.forms.get("exectype")
    exectype = exectype.strip()
    # print "exectype:",exectype
    runtype = request.forms.get("runtype")
    runtype = runtype.strip()
    runtype = runtype.lower()
    exectype = exectype.lower()
    autodefect = request.forms.get("autodefect")
    autodefect = autodefect.strip()
    schedulerun = request.forms.get("schedulerun")
    schedulerun = schedulerun.strip()
    filenames = filenames.replace(",", " ")
    iteration_value = request.forms.get("iterationval")

    print "iteration_Value" + iteration_value
    # print filenames
    # print exectype
    # print autodefect
    # print schedulerun
    # print exectype
    if exectype == "run keywords in parallel":
        print "matched"
        exectype = "-kwparallel"
    else:
        exectype = ""

    if runtype == "sequential":
        runtype = "-tcsequential"
    elif runtype == "parallel":
        runtype = "-tcparallel"
    elif runtype == "rmt":
        runtype = "-RMT"
    elif runtype == "ruf":
        runtype = "-RUF"
    elif runtype == "rup":
        runtype = "-RUP"

    print autodefect

    if autodefect == "" or autodefect == "None":
        autodefect = ""
    else:
        autodefect = "-ad -jiraproj " + autodefect

    if schedulerun == "y":
        schedulerun = request.forms.get("datevalue")
        schedulerun = "-schedule " + schedulerun.strip()
    else:
        schedulerun = ""

    cfg = readconfig()
    python_path = cfg['pythonpath']
    if python_path == "":
        if platform.system() != "Windows":
            python_path = "python "
    else:
        python_path += " "
    print cfg
    Warrior_location = cfg['pythonsrcdir']
    toolname = ''
    with open(NAMEFILE) as f:
        toolname = f.read().strip()

    # logfile_config = open("warriorlog_location.dat")
    # logfile_location = logfile_config.read()
    # logfile_location = logfile_location.strip()

    command_To_Run = python_path + Warrior_location + os.sep + toolname

    if autodefect != "":
        command_To_Run += " " + autodefect

    if exectype != "":
        command_To_Run += " " + exectype

    if runtype != "":
        if (runtype == "-RMT") or (runtype == "-RUF") or (runtype == "-RUP"):
            command_To_Run += " " + runtype + " " + iteration_value
        else:
            command_To_Run += " " + runtype

    if schedulerun != "":
        command_To_Run += " " + schedulerun

    # File Name should be there by default
    command_To_Run += " " + filenames

    # print "Command:: " + command_To_Run
    # current_timestamp = time.time()
    # logFileName = logfile_location + "/" + datetime.datetime.fromtimestamp(current_timestamp).strftime('%Y%m%d_%H%M%S') + ".log"

    if platform.system() == "Linux":
        os.system(
            "gnome-terminal -e 'bash -c " + "\"" + "source ~/.bashrc" + " && " + command_To_Run + " ; exec bash\"'")
        command_response.append({'command_to_run': command_To_Run,
                                 'Execution_Result': 'Command has been sent to Linux terminal for execution'})
    elif platform.system() == "Windows":
        os.system("start /wait cmd /k python " + command_To_Run)
        command_response.append({'command_to_run': command_To_Run,
                                 'Execution_Result': 'Command has been sent to Windows command prompt for execution'})

    # command_response.append({'command_to_run': command_To_Run})
    # Delegate command to shell
    # result_exec = subprocess.Popen(command_To_Run, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    # value = iter(result_exec.stdout.readline, b'')

    # print command_response
    return json.dumps(command_response)


JIRACONFIGFILE = './config/data.json'


@route('/get_jira_projects')
def get_jira_projects():
    node_dict = {}
    node_dict[1] = "None"
    id = 2
    path = readconfig()
    xml_file = os.path.join(path["pythonsrcdir"], "Tools", "Jira",
                            "jira_config.xml")
    if os.path.exists(xml_file):
        tree = xml.etree.ElementTree.parse(xml_file)
        try:
            root = tree.getroot()
        except:
            print("No root node found!!")
        else:
            for nodes in root:
                if nodes.tag == "system":
                    if "name" in nodes.attrib:
                        node_dict[id] = nodes.attrib["name"]
                        id += 1
    return node_dict


def populate_child_tags(some_string, parent_dir_name, dirs):
    if dirs:
        for dir in dirs:
            for root, dirs, files in os.walk(
                    os.path.join(parent_dir_name, dir)):
                some_string += '{"dir": '
                some_string = some_string + '"' + dir + '",\n'
                if files:
                    file_name_string = '[ '
                    for filename in files:
                        if file_name_string == '[ ':
                            file_name_string = file_name_string + '"' + filename + '"'
                        else:
                            file_name_string = file_name_string + ', "' + filename + '"'
                    file_name_string += ' ],'
                    some_string = some_string + '"file": ' + file_name_string
                some_string += '"children": [\n'
                some_string = populate_child_tags(some_string, root, dirs)
                some_string += ']},'
                break
    some_string = some_string[:-1]
    return some_string


@route('/get_paths/:path')
def get_files_and_folders(path):
    path = path.replace(">", os.sep)
    drive = os.path.basename(path)
    some_string = '{\n'
    # Commented code gets all files and folders
    # az = lambda: (chr(i)+":\\" for i in range(ord("A"), ord("Z") + 1))
    # for drive in az():
    for root, dirs, files in os.walk(path):
        some_string += '"dir": '
        some_string = some_string + '"' + drive + '",\n'
        if files:
            file_name_string = '[ '
            for file in files:
                if file_name_string == '[ ':
                    file_name_string = file_name_string + '"' + file + '"'
                else:
                    file_name_string = file_name_string + ', "' + file + '"'
            file_name_string += ' ],'
            some_string = some_string + '"file": ' + file_name_string
        some_string += '"children": [\n'
        some_string = populate_child_tags(some_string, root, dirs)
        some_string += ']}\n'
        break

    with open(DATAFILE, "w") as outfile:
        outfile.write(some_string)


if __name__ == '__main__':
    port_parser = argparse.ArgumentParser()
    port_parser.add_argument('-p', help='enter a port number here')
    result = port_parser.parse_args()
    try:
        if result.p:
            run(host='0.0.0.0', port=int(result.p), debug=True, reloader=True)
        else:
            run(host='0.0.0.0', port=5000, debug=True, reloader=True)
    except:
        print "The selected port is already in use, please use -p port_number to choose another port"
        exit(1)

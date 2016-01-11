import sys
import re
import os
import shutil


def cmd_getargs():
    arg_dict = {}

    tmp_key = ""
    tmp_value = ""

    start = 0
    for single_arg in sys.argv:
        if single_arg[0] and single_arg[0] == '-':
            start = 1
            tmp_key = single_arg[1:]
        else:
            if start == 1:
                tmp_value = single_arg

        if len(tmp_key) and len(tmp_value):
            arg_dict[tmp_key] = tmp_value
            tmp_key = ""
            tmp_value = ""

    return arg_dict


def protos_in_dir(path):
    path_array = []
    for root, dirs, files in os.walk(path):
        subfiles = os.listdir(root)
        for fn in subfiles:
            fpath = root + "/" + fn
            fextension = fn[fn.rfind('.'):]
            if os.path.isfile(fpath) and fextension == ".proto":
                path_array.append(fpath)
    return path_array


def regex_find_first(path, rgstr):
    # open the file
    f = open(path, "r")
    content = f.read()
    f.close()

    # replace
    pattern = re.compile(rgstr)
    results = pattern.findall(content)
    if len(results) > 0:
        return results[0]
    return ""


def regex_find_all_import(path):
    # open the file
    f = open(path, "r")
    content = f.read()
    f.close()

    # replace
    pattern = re.compile("""import[ ]+"[a-z,A-Z,0-9,.]*"[ ]*;""")
    results = pattern.findall(content)

    ret = []
    for str in results:
        ret.append(str.split("\"")[1])

    return ret


def regex_find_all_message(path):
    # open the file
    f = open(path, "r")
    content = f.read()
    f.close()

    # replace
    pattern = re.compile("""message[ ]+[a-z,A-Z,0-9]+.+""")
    results = pattern.findall(content)

    pattern = re.compile("""enum[ ]+[a-z,A-Z,0-9]+.+""")
    results += pattern.findall(content)

    ret = []
    for str in results:
        tmp = str.split(" ")[1]
        if tmp[-1] == "{":
            tmp = tmp[:-1]
        ret.append(tmp)
    return ret


def regex_replace(path, rgstr, rpstr):
    # open the file
    f = open(path, "r")
    content = f.read()
    f.close()

    # replace
    new_content = re.sub(rgstr, rpstr, content)

    # save to file
    f = open(path, "w")
    f.write(new_content)
    f.close()


def regex_replace_import(path, old_import, old_msg, new_msg):
    # open the file
    f = open(path, "r")
    content = f.read()
    f.close()

    # replace import to placeholder
    str_import = """import[ ]+""" + "\"" + old_import + """.proto"[ ]*;"""
    pattern = re.compile(str_import)
    arr = pattern.findall(content)
    old_str_import = ""

    if len(arr) == 0:
        print("find [" + old_import + "] in [" + path + "] failed!")
        return

    old_str_import = arr[0]
    place_holder_import = """---place_holder_import---"""
    content = re.sub(old_str_import, place_holder_import, content)

    # replace java_outer_classname to placeholder
    str_java = """option[ ]+java_outer_classname[ ]*=[ ]*"[a-z,A-Z,0-9,.]*";"""
    pattern = re.compile(str_java)
    arr = pattern.findall(content)
    old_java = ""

    if len(arr) == 0:
        print("find [" + old_import + "] in [" + path + "] failed!")
        return

    old_str_java = arr[0]
    place_holder_java = """---place_holder_java---"""
    content = re.sub(old_str_java, place_holder_java, content)

    pattern = re.compile(" " + new_msg)
    arr = pattern.findall(content)
    if len(arr) > 0:
        # print(new_msg + " in " + path + " does not need to replace!")
        return

    str_sub_proto = """proto.""" + old_msg
    pattern = re.compile(str_sub_proto)
    arr = pattern.findall(content)
    if len(arr) > 0:
        content = re.sub(" " + str_sub_proto, " " + new_msg, content)
    else:
        content = re.sub(" " + old_msg, " " + new_msg, content)

    content = re.sub(place_holder_import, old_str_import, content)
    content = re.sub(place_holder_java, old_str_java, content)

    # save to file
    f = open(path, "w")
    f.write(content)
    f.close()


def __main__():
    arg_dict = cmd_getargs()

    if not arg_dict.has_key("p"):
        print("please use -p [proto path] cmd to pass param")
        return

    proto_path = arg_dict["p"]

    os.chdir(proto_path)
    os.system("git reset --hard")
    os.system("git clean -fd")
    # os.system("git pull --all")

    all_files = protos_in_dir(proto_path)
    need_import_files = []
    for spath in all_files:
        # print(spath)

        base_name = os.path.basename(spath)
        package_name, ext = os.path.splitext(base_name)
        # print(package_name)

        import_msg = regex_find_first(spath, """import[ ]+"[a-z,A-Z,0-9,.]*"[ ]*;""")
        regex_replace(spath, "package[ ]+proto;", "package " + package_name + ";")
        if import_msg != "":
            need_import_files.append(spath)
            # else:
            # print("changed package name: " + spath)

    # print("\nfor import:\n")
    for spath in need_import_files:
        # print(spath)

        ffolder, fname = os.path.split(spath)

        all_imports = regex_find_all_import(spath)
        # print(all_imports)

        for import_msg in all_imports:
            all_msg = regex_find_all_message(ffolder + "/" + import_msg);
            # print(all_msg)

            package_name, ext = os.path.splitext(import_msg)
            for msg in all_msg:
                regex_replace_import(spath, package_name, msg, package_name + "." + msg)

    for spath in all_files:
        base_name = os.path.basename(spath)
        package_name, ext = os.path.splitext(base_name)
        cmd = "protoc " + base_name + " -o " + package_name + ".pb"
        os.system(cmd)

    pb_path = os.path.join(proto_path, "pb")
    if os.path.isdir(pb_path):
        os.system("rm -rf " + pb_path)
    os.makedirs(pb_path)
    for root, dirs, files in os.walk(proto_path):
        subfiles = os.listdir(root)
        for fn in subfiles:
            fpath = root + "/" + fn
            fextension = fn[fn.rfind('.'):]
            if os.path.isfile(fpath) and fextension == ".pb":
                shutil.move(fpath, os.path.join(pb_path, fn))

    os.system("git reset --hard")

__main__();

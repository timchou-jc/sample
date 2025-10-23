import os, platform, sys, subprocess
from pathlib import Path

#windows platform specific import
if sys.platform == 'win32':
    import winreg as winreg


def writePathOption(content, option, path):
    content.append(option + ' "' + path + '"\n')

def writeSystemDefine(content, option, value):
    content.append("-sd")
    content.append('"' + option + '=' + value + '"\n')


def writeSuppressedInclude(content, path, isSystem):
    writePathOption(content, "-si" if isSystem else "-i", path)
    writePathOption(content, "-q", path)


def writeSuppressedSystemInclude(content, path):
    writeSuppressedInclude(content, path, isSystem=True)


def filter_stub_list(stubdir):
    stublist = []
    for root, dirs, files in os.walk(stubdir, topdown=True):
        for dirname in dirs:
            nocip_path = os.path.join(root, dirname, ".nocip")
            if os.path.exists(nocip_path):
                dirs.remove(dirname)
            else:
                stublist.append(os.path.join(root, dirname))
    return stublist


def generateStubs(cctFilePath, cipContent, msvsVersion, language=None, osSize=None):
    # Stub directory is not in the usual location as we are running a script from common
    cctDirName = os.path.basename(cctFilePath).strip('.cct')
    if cctDirName.startswith("generated_cct_"):
        stub_cct_dir_name = "MS_VS_{}_{}_{}".format(
            msvsVersion,
            "x86" if osSize == "32" else "x64",
            language
        )
    else:
        stub_cct_dir_name = cctDirName
    myStubDir = os.path.abspath(
        os.path.join(
            cctFilePath,
            "..", "DATA",
            stub_cct_dir_name,
            "Stub"
        )
    )

    if os.path.isdir(myStubDir):
        stubList = filter_stub_list(myStubDir)

        for name in stubList:
            writeSuppressedInclude(cipContent, name, isSystem=False)
        for scriptFilename in stubList:
            if scriptFilename.endswith("forceinclude"):
                firstList = []
                fileList = []
                firstFile = "vc" + msvsVersion + ".h"
                for x in os.listdir(scriptFilename):
                    if x == firstFile:
                        firstList.append(x)
                    else:
                        fileList.append(x)
                firstList.sort()
                fileList.sort()
                for fn in firstList + fileList:
                    writePathOption(cipContent, "-fi",
                                    os.path.join(scriptFilename, fn))
    return cipContent


#Pass Installation registry KEY NAME along with VALUE NAME
def getHklmRegValue(keyName, valueName):
    reg = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
    key = winreg.OpenKey(reg, keyName)
    value = winreg.QueryValueEx(key, valueName)
    winreg.CloseKey(key)
    return value[0]

def getSoftware32Or64RegValue(keyName, valueName, osSize):

    if platform.machine() == "AMD64" and osSize == "32":
        try:
            return getHklmRegValue("SOFTWARE\\Wow6432Node\\" + keyName, valueName)
        except WindowsError: pass
    else:
        try:
            return getHklmRegValue("SOFTWARE\\" + keyName, valueName)
        except WindowsError: pass
        try:
            return getHklmRegValue("SOFTWARE\\Wow6432Node\\" + keyName, valueName)
        except WindowsError: pass

    return None

def mapMsvcToCl(myCip, msvcVersion):
    if msvcVersion == '14.0':
        return '19'  # 2015
    elif msvcVersion == '14.1':
        return '19'  # 2017
    elif msvcVersion == '14.2':
        return '19'  # 2019
    elif msvcVersion == '14.3':
        return '19'  # 2022

    myCip.exit_error(20, "Unsupported MSVC version; " + msvcVersion)
    return None

def mapMsvcToVsVers(myCip, msvcVersion):
    if msvcVersion == '14.0':
        return '14'  # 2015
    elif msvcVersion == '14.1':
        return '15'  # 2017
    elif msvcVersion == '14.2':
        return '16'  # 2019
    elif msvcVersion == '14.3':
        return '17'  # 2012

    myCip.exit_error(20, "Unsupported MSVC version; " + msvcVersion)
    return None

def getVswhere(myCip):
    vswhere = os.path.expandvars("%ProgramFiles(x86)%\\Microsoft Visual Studio\\Installer\\vswhere.exe")
    if not os.path.exists(vswhere):
        vswhere = os.path.expandvars("%ProgramFiles%\\Microsoft Visual Studio\\Installer\\vswhere.exe")

    if not os.path.exists(vswhere):
        myCip.exit_error(21, "Unable to locate; vswhere")

    return vswhere


def try_decoding(raw_output):
    try:
        return raw_output.decode('utf-8')
    except UnicodeDecodeError:
        pass
    return raw_output.decode('sjis')

def source_bat(bat_file, params):
    result = {}
    cmd = '"%s"%s & set' % (bat_file, params)
    print('Setting Environment:', cmd)

    process = subprocess.Popen(cmd,
                        stdout=subprocess.PIPE,
                        shell=True)
    (out, err) = process.communicate()

    for line in try_decoding(out).split("\n"):
        if '=' not in line:
            continue
        line = line.strip()
        key, value = line.split('=', 1)
        result[key]=value

    return result

def getEnvVarsWithVswhere(msvcVersion, myCip, osSize):
    vsVars = {}
    if float(msvcVersion) >= 14.1:
        vsVersion = mapMsvcToVsVers(myCip, msvcVersion)
        vsNextVersion = str(int(vsVersion) + 1)
        cmd = " -version [{0},{1}) -products * -property installationPath ".format(vsVersion, vsNextVersion)

        proc = subprocess.Popen(getVswhere(myCip) + cmd, stdout=subprocess.PIPE)
        procout = try_decoding(proc.stdout.read().rstrip().splitlines()[0])
        vsdevToolsCmd = procout + "\\Common7\\Tools\\vsdevcmd.bat"

        params = " -arch="
        if osSize == "32":
            params += "x86"
        else:
            params += "amd64"

        specific_SDK = os.getenv('HELIX_QAC_WIN_SDK')  # None
        if specific_SDK:
            params += " -winsdk="
            params += specific_SDK

        vsVars = source_bat(vsdevToolsCmd, params)

    return vsVars

def getCLVersionFromRegistry(myCip, msvcVersion, osSize):
    major = mapMsvcToCl(myCip, msvcVersion)

    if float(msvcVersion) < 14.1:
        vers = str(int(float(msvcVersion))) + ".0"
        minor = getSoftware32Or64RegValue("Microsoft\\VisualStudio\\" + vers + "\\VC\\Runtimes\\x86", "Minor", osSize)
        build = getSoftware32Or64RegValue("Microsoft\\VisualStudio\\" + vers  + "\\VC\\Runtimes\\x86", "Bld", osSize)

        if minor is None:
            minor = getSoftware32Or64RegValue("Microsoft\\VisualStudio\\" + vers + "\\VC\\Runtimes\\x64", "Minor", osSize)
            build = getSoftware32Or64RegValue("Microsoft\\VisualStudio\\" + vers + "\\VC\\Runtimes\\x64", "Bld", osSize)

    return "{:0>2}".format(major), "{:0>2}".format(minor), "{:0>5}".format(build)

def getVCVersionFromRegistry(msvcVersion, osSize):
	major = msvcVersion.split('.')[0]

	vers = str(int(float(msvcVersion))) + ".0"
	minor = getSoftware32Or64RegValue("Microsoft\\VisualStudio\\" + vers + "\\VC\\Runtimes\\x86", "Minor", osSize)
	build = getSoftware32Or64RegValue("Microsoft\\VisualStudio\\" + vers  + "\\VC\\Runtimes\\x86", "Bld", osSize)

	if minor is None:
		minor = getSoftware32Or64RegValue("Microsoft\\VisualStudio\\" + vers + "\\VC\\Runtimes\\x64", "Minor", osSize)
		build = getSoftware32Or64RegValue("Microsoft\\VisualStudio\\" + vers + "\\VC\\Runtimes\\x64", "Bld", osSize)

	return "{:0>2}".format(major), "{:0>2}".format(minor), "{:0>5}".format(build)

def getNETFrameworkLocation(osSize):
     return getSoftware32Or64RegValue("Microsoft\\.NETFramework\\", "InstallRoot", osSize)

def getWinLibLocation(regKey, valueName, valueName2, osSize):
    value = getSoftware32Or64RegValue(regKey, valueName, osSize)
    if value is None and not valueName2 is None:
        value = getSoftware32Or64RegValue(regKey, valueName2, osSize)
    return value


def msvcCipFile(
    myCip, msvcVersion, msvsVersion, isSdkAddDirs, regKey, valueName, valueName2=None, language=None, osSize=None
):
    cipContent = []

    generateStubs(myCip.cctFilePath(), cipContent, msvsVersion, language=language, osSize=osSize)

    # Checking if Visual Studio Installation registry entry is available
    if float(msvcVersion) < 14.1:
        VSInstall = getSoftware32Or64RegValue("Microsoft\\VisualStudio\\" + msvcVersion + "\\setup\\VC", "ProductDir", osSize)
    else:
        VSEnvVars = getEnvVarsWithVswhere(msvcVersion, myCip, osSize)
        vcPath = VSEnvVars['VCToolsInstallDir']
        VSInstall = vcPath

    # If compiler Installation not found then create cip file with Error message
    if VSInstall is None:
        myCip.exit_error(
            10,
            "Visual Studio {} Compiler installation registry is not valid".format(msvsVersion)
        )

    # Write to cip
    if float(msvcVersion) < 14.1:
        writeSuppressedSystemInclude(cipContent, os.path.join(VSInstall, 'include'))
        writeSuppressedSystemInclude(cipContent, os.path.join(VSInstall, 'atlmfc', 'include'))
    else:  # VS 2017 onwards includes env var
        if 'VCToolsVersion' in VSEnvVars:
            VCToolsVersion = VSEnvVars['VCToolsVersion']
        elif 'VSCMD_VER' in VSEnvVars:
            VCToolsVersion = VSEnvVars['VSCMD_VER']

        if VCToolsVersion is not None:
            msver = VCToolsVersion.replace('14.', '19')
            msver = msver.replace('.', '')
            writeSystemDefine(cipContent, "_MSC_FULL_VER", msver)
            writeSystemDefine(cipContent, "_MSC_VER", msver[:4])

        if 'WindowsSDKVersion' in VSEnvVars:
            writeSystemDefine(cipContent, "WindowsSDKVersion", VSEnvVars['WindowsSDKVersion'])

        VSIncludeEnv = VSEnvVars['INCLUDE'].rstrip(';')
        VSInclude = VSIncludeEnv.split(';')
        VSToolsInstallDir = VSEnvVars['VCToolsInstallDir']
        for vsInclude in VSInclude:
            writeSuppressedSystemInclude(cipContent, vsInclude)
            if isSdkAddDirs and not vsInclude.startswith(VSToolsInstallDir):
                WinSDKList = [os.path.join(d, t) for d, ds, fs in os.walk(vsInclude) for t in ds]
                for sdkName in WinSDKList:
                    writeSuppressedSystemInclude(cipContent, sdkName)

    # Checking if Microsoft KitRoot registry entry is available
    WinKitRoot = getWinLibLocation(regKey, valueName, valueName2, osSize)
    if WinKitRoot is None:
        myCip.exit_error(11, "Can Not Find Microsoft KitRoot registry entry")
    WinKitRootInclude = os.path.join(WinKitRoot, 'Include')

    if float(msvcVersion) >= 14.0 and float(msvcVersion) < 14.1:
        maj, min, bld = getCLVersionFromRegistry(myCip, msvcVersion, osSize)
        vcVersion = maj + min + bld;
        writeSystemDefine(cipContent, "_MSC_FULL_VER", vcVersion)
        writeSystemDefine(cipContent, "_MSC_VER", maj + min)
        vcInclude = getSoftware32Or64RegValue(regKey, valueName2, osSize)
        vcInclude = os.path.join(vcInclude, r'Include')

        dirs = [f for f in os.listdir(vcInclude) if os.path.isdir(os.path.join(vcInclude, f))]
        for dir in dirs:
            writeSuppressedSystemInclude(cipContent, os.path.join(vcInclude, dir, r'ucrt'))

    if float(msvcVersion) < 14.1:
        writeSuppressedSystemInclude(cipContent, WinKitRootInclude)

        if isSdkAddDirs:
            WinSDKList = [os.path.join(d, t) for d, ds, fs in os.walk(WinKitRootInclude) for t in ds]
            for sdkName in WinSDKList:
                writeSuppressedSystemInclude(cipContent, sdkName)
    else: # 2017 onwards
        WinKitEnv = VSEnvVars['WindowsLibPath'].rstrip(';')
        WinKit = WinKitEnv.split(';')
        for kit in WinKit:
            writeSuppressedSystemInclude(cipContent, kit)

    try:
        cipFilepath = myCip.cipFilePath()
        cipFile = open(cipFilepath, "w")
        cipFile.writelines(cipContent)
        cipFile.close()

    except :
        myCip.exit_error(100, "Unable to write to CIP")

def cl19(myCip, language, osSize):
    msvcCipFile(myCip, "14.0", "2015", True, r"Microsoft\Windows Kits\Installed Roots", "KitsRoot81", "KitsRoot10", language=language, osSize=osSize)

def cl19_1(myCip, language, osSize):
    msvcCipFile(myCip, "14.1", "2017", True, r"Microsoft\Windows Kits\Installed Roots", "KitsRoot10", language=language, osSize=osSize)

def cl19_2(myCip, language, osSize):
    msvcCipFile(myCip, "14.2", "2019", True, r"Microsoft\Windows Kits\Installed Roots", "KitsRoot10", language=language, osSize=osSize)

def cl19_3(myCip, language, osSize):
    msvcCipFile(myCip, "14.3", "2022", True, r"Microsoft\Windows Kits\Installed Roots", "KitsRoot10", language=language, osSize=osSize)


def main():
    qafDir = str(Path(__file__).parent.joinpath('..', 'core_qaf').resolve())
    if qafDir not in sys.path:
        sys.path.insert(0, qafDir)

    try:
        import qaf
        myCip = qaf.Cip(str(Path(__file__).resolve()))

        my_cct = qaf.Cct(myCip.cctFilePath())

        os_sizes = {
            "x86": "32",
            "x64": "64",
        }
        osSize = os_sizes.get(my_cct.header()["HOST"], None)
        if osSize is None:
            myCip.exit_error(1, "Platforms other than 32 or 64 bits are not currently supported.")

        language = my_cct.header().get("SOURCE_LANGUAGE", None)
        if language is None:
            myCip.exit_error(2, "Languages other than C and C++ are not currently supported.")

        if sys.platform != "win32":
            myCip.exit_error(3, "Visual Studio is only supported on Windows")

        version_cipfile_map = {
            "19-3": cl19_3,
            "19-2": cl19_2,
            "19-1": cl19_1,
            "19": cl19
        }
        cip_file_class = version_cipfile_map.get(my_cct.header()["COMPILER_VERSION"], None)
        try:
            cip_file_class(myCip, language, osSize)
        except TypeError:
            myCip.exit_error(4, "Unsupported Visual Studio version.")

        myCip.exit_success()

    except ModuleNotFoundError:
        print('Unable to locate "qaf.py" module. Exiting.',file=sys.stdout)
        sys.exit(1)

if __name__ == "__main__":
    """
    Generate a CIP for Visual Studio

    If debugging and running standalone ensure the first parameter is the full path to the CCT
    and the second is a pipe name - "stdout" or "stderr" will output any messages that would of
    been sent back to Framework to the console. Eg

    python msvc.py "C:\sample_projects\VS_CIP\prqa\configs\Initial\config\MS_VC++_CL_19_x86_C.cct" stderr

    Any non zero exit status indicates an error.
    """  # noqa
    main()

#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Helper Backend Tools in the BackendTools Package for WxFixBoot Version 2.0~pre1
# This file is part of WxFixBoot.
# Copyright (C) 2013-2016 Hamish McIntyre-Bhatty
# WxFixBoot is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3 or,
# at your option, any later version.
#
# WxFixBoot is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with WxFixBoot.  If not, see <http://www.gnu.org/licenses/>.

#Do future imports to prepare to support python 3. Use unicode strings rather than ASCII strings, as they fix potential problems.
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

#Begin Main Class. *** These need testing and refactoring ***
class Main():
    def FindMissingFSCKModules(self):
        """Check for and return all missing fsck modules (fsck.vfat, fsck.minix, etc)."""
        logger.info("HelperBackendTools: Main().FindMissingFSCKModules(): Looking for missing FSCK modules to ignore...")
        FailedList = []

        Keys = DiskInfo.keys()
        Keys.sort()

        for Disk in Keys:
            FSType = DiskInfo[Disk]["FileSystem"]

            #Check the FSType is known.
            if FSType not in ("Unknown", "N/A"):
                #Check if this module is present.
                Retval = CoreTools.StartProcess("which fsck."+FSType, ShowOutput=False)

                if Retval != 0:
                    #OS probably couldn't find it, add it to the failed list.
                    logger.warning("HelperBackendTools: Main().FSCKModules(): Couldn't find FSCK module: fsck."+FSType+"! Adding it to the list of missing modules...")
                    FailedList.append("fsck."+FSType)

                else:
                    logger.debug("HelperBackendTools: Main().FSCKModules(): Found fsck."+FSType+"...")

        #Return the list, so FSCheck functions know which FSes to ignore.
        logger.info("HelperBackendTools: Main().FindMissingFSCKModules(): Done! Missing FSCK modules: "+', '.join(FailedList))
        return FailedList

    def LookForAPTOnPartition(self, APTExecCmds): #*** Maybe move to startup tools on switch to dictionaries *** *** Does this need to be in a function? ***
        """Look for apt using the command lists given (they include the partition, by the way)."""
        logger.debug("HelperBackendTools: Main().LookForAPTOnPartition(): Running "+APTExecCmds+"...")

        Retval = CoreTools.StartProcess(APTExecCmds, ShowOutput=False)

        if Retval != 0:
            #Couldn't find apt!
            logger.info("HelperBackendTools: Main().LookForAPTOnPartition(): Didn't find apt...")
            return False

        else:
            #Found APT!
            logger.info("HelperBackendTools: Main().LookForAPTOnPartition(): Found apt...")
            return True

    def LookForBootloaderOnPartition(self, Bootloader, PackageManager, MountPoint, UsingChroot): #*** Test again *** *** Maybe move this to MainStartupTools later ***
        """Look for the currently installed bootloader in the given mount point."""
        logger.debug("HelperBackendTools: Main().LookForBootloaderOnPartition(): Looking for "+Bootloader+" in "+MountPoint+"...")

        #Okay, let's run a command in the chroot that was set up in self.FindBootloaderRemovalOSs(), depending on which package manager this OS uses, and which bootloader is currently installed.
        if PackageManager == "apt-get":
            Cmd = "dpkg --get-selections"

        if UsingChroot:
            Cmd = "chroot "+MountPoint+" "+Cmd

        Output = CoreTools.StartProcess(Cmd, ShowOutput=False, ReturnOutput=True)[1].split("\n")
        Packages = []

        if Bootloader == "GRUB-LEGACY":
            for Package in Output:
                if "grub" in Package and "install" in Package and "grub2" not in Package:
                    Packages.append(Package.split()[0])

        elif Bootloader == "GRUB2":
            for Package in Output:
                if "grub-pc" in Package and "install" in Package:
                    Packages.append(Package.split()[0])

        elif Bootloader == "LILO":
            for Package in Output:
                if "lilo" in Package and "install" in Package:
                    Packages.append(Package.split()[0])

        elif Bootloader == "GRUB-UEFI":
            for Package in Output:
                if "grub-efi" in Package and "install" in Package:
                    Packages.append(Package.split()[0])

        elif Bootloader == "ELILO":
            for Package in Output:
                if "elilo" in Package and "install" in Package:
                    Packages.append(Package.split()[0])

        #Now we can check the return value. If it's 0, the bootloader is present in this OS. Otherwise, it isn't.
        if Packages != []:
            logger.info("HelperBackendTools: Main().LookForBootloaderOnPartition(): Found "+Bootloader+" in "+MountPoint+"...")
            return True

        else:
            logger.info("HelperBackendTools: Main().LookForBootloaderOnPartition(): Didn't find "+Bootloader+" in "+MountPoint+"...")
            return False

    def FindCheckableFileSystems(self, AutoRootFS): #*** Tidy this up later ***
        """Find all checkable filesystems, and then return them to MainBackendTools().BadSectorCheck()/MainBackendTools().QuickFSCheck()"""
        logger.info("HelperBackendTools: Main().FindCheckableFileSystems(): Finding and returning all filesystems/partitions that can be checked...")

        #Do setup.
        DoNotCheckList = []
        CheckList = []

        #Get a list of missing fsck modules (if any) based on the existing filesystems.
        MissingFSCKModules = self.FindMissingFSCKModules()

        Keys = DiskInfo.keys()
        Keys.sort()

        #Determine checkable partitions.
        for Disk in Keys:
            #Make sure we're looking at a partition, if not, ignore it.
            if DiskInfo[Disk]["Type"] == "Partition":
                #Get the FSType.
                FSType = DiskInfo[Disk]["FileSystem"]

                #Check if the required fsck module is present, and that the partition isn't RootFS
                if "fsck."+FSType not in MissingFSCKModules and FSType not in ("Unknown", "N/A"):
                    #If we're not running on a live disk, skip the filesystem if it's the same as RootFS (in which case checking it may corrupt data)
                    if SystemInfo["IsLiveDisk"] == False and Disk == AutoRootFS:
                        CheckTheFS = False
                        RemountPartitionAfter = False
                        continue

                    #Check if the partition is mounted.
                    PartitionIsMounted = CoreTools.IsMounted(Disk)

                    if PartitionIsMounted == False:
                        #Not mounted.
                        CheckTheFS = True
                        RemountPartitionAfter = False

                    else:
                        #Unmount the FS temporarily, to avoid data corruption.
                        Retval = CoreTools.Unmount(Disk)

                        if Retval != 0:
                            logger.warning("HelperBackendTools: Main().FindCheckableFileSystems(): Failed to unmount "+Disk+", which is necessary for safe disk checking! Ignoring it, becuase it's probably a home directory (if running an OS on the HDD, and not a live disk) or an essential system dir...")
                            CheckTheFS = False
                            RemountPartitionAfter = False

                        else:
                            CheckTheFS = True
                            RemountPartitionAfter = True
                else:
                    CheckTheFS = False
                    RemountPartitionAfter = False

                if CheckTheFS == False:
                    #Add it to the non-checkable list
                    DoNotCheckList.append(Disk+" with Filesystem: "+FSType)

                else:
                    #Add it to the list for checking.
                    CheckList.append(Disk+" "+FSType+" "+unicode(RemountPartitionAfter))

        #Report uncheckable partitions.
        if DoNotCheckList != []:
            #Some filesystems will not be checked. Tell the user.
            DialogTools.ShowMsgDlg(Kind="info", Message="The following filesystems will not be checked:\n\n"+'\n'.join(DoNotCheckList)+".\n\nThe most likely reason for this is that some of the filesystems are in use, or that the required filesystem checkers weren't found. WxFixBoot will now continue to check the remaining filesystems.")

        logger.info("HelperBackendTools: Main().FindCheckableFileSystems(): Done! Filesystems that won't be checked: "+'\n'.join(DoNotCheckList)+"...")
        return CheckList

    def HandleFilesystemCheckReturnValues(self, ExecList, Retval, Partition, OSsForBootloaderRemoval, OSsForBootloaderInstallation):
        """Handle Filesystem Checker return codes."""
        #Return values of 1,2 or 3 happen if errors were corrected.
        if Retval in (1, 2, 3):
            if ExecList[0] == "xfs_repair":
                #Fs Corruption Detected.
                logger.warning("HelperBackendTools: Main().HandleFilesystemCheckReturnValues(): xfs_repair detected filesystem corruption on FileSystem: "+Partition+". It's probably (and hopefully) been fixed, but we're logging this anyway.")
                DialogTools.ShowMsgDlg(Kind="warning", Message="Corruption was found on the filesystem: "+Partition+"! Fortunately, it looks like the checker utility has fixed the corruption. Click okay to continue.")

            elif ExecList[0] in ('fsck.jfs', 'fsck.minix', 'fsck.reiserfs', 'fsck.vfat', 'fsck.ext2', 'fsck.ex3', 'fsck.ext4', 'fsck.ext4dev'):
                #Fixed Errors.
                logger.info("HelperBackendTools: Main().HandleFilesystemCheckReturnValues(): "+ExecList[0]+" successfully fixed errors on the partition: "+Partition+". Continuing...")
                DialogTools.ShowMsgDlg(Kind="warning", Message="The filesystem checker found and successfully fixed errors on partition: "+Partition+". Click okay to continue.")

        else:
            #Something bad happened! *** Check if we're actually doing bootloader operations first! ***
            logger.error("HelperBackendTools: Main().HandleFilesystemCheckReturnValues(): "+ExecList[0]+" Errored with exit value "+unicode(retval)+"! This could indicate filesystem corruption or bad sectors! Asking the user whether to skip any bootloader operations...")

            Result = DialogTools.ShowYesNoDlg(Message="Error! The filesystem checker gave exit value: "+unicode(retval)+"! This could indicate filesystem corruption, a problem with the filesystem checker, or bad sectors on partition: "+Partition+". If you perform bootloader operations on this partition, WxFixBoot could become unstable, and your system could become unbootable. Do you want to disable bootloader operations, as is strongly recommended?", Title="WxFixBoot - Disable Bootloader Operations?")

            if Result:
                #A good choice. WxFixBoot will now disable any bootloader operations.
                logger.warning("HelperBackendTools: Main().HandleFilesystemCheckReturnValues(): User disabled bootloader operations as recommended, due to bad sectors/HDD problems/FS Checker problems...")

                OSsForBootloaderRemoval = []
                OSsForBootloaderInstallation = ["None,FSCKProblems"]
                return OSsForBootloaderRemoval, OSsForBootloaderInstallation

            else:
                #Seriously? Well, okay, we'll do it anyway... This is probably a very bad idea...
                logger.warning("HelperBackendTools: Main().HandleFilesystemCheckReturnValues(): User ignored the warning and went ahead with bootloader modifications (if any) anyway, even with possible HDD problems/Bad sectors! This is a REALLY bad idea, but we'll do it anyway, as requested...")

                return OSsForBootloaderRemoval, OSsForBootloaderInstallation

    def AskUserForBootloaderInstallationOSs(self, OSListWithPackageManagers, UpdateBootloader, ReinstallBootloader, OSsForBootloaderRemoval): #*** Maybe move to BootloaderTools package ***
        """Ask the user where the new bootloader is to be installed."""
        #*** Temporarily define this as global until switch to dictionaries ***
        global OSsForBootloaderInstallation
        OSsForBootloaderInstallation = []

        if len(OSListWithPackageManagers) == 1:
            if UpdateBootloader:
                DialogTools.ShowMsgDlg(Kind="info", Message="Your bootloader will be updated.")

            else:
                DialogTools.ShowMsgDlg(Kind="info", Message="Your bootloader will be removed from the following Operating Systems ("+', '.join(OSsForBootloaderRemoval)+").")

            OSsForBootloaderInstallation = OSListWithPackageManagers[:]
            logger.info("HelperBackendTools: Main().AskUserForInstallationOSs(): Installing the new bootloader in OS(s): "+', '.join(OSsForBootloaderInstallation))

        else:
            if UpdateBootloader or ReinstallBootloader:
                DialogTools.ShowMsgDlg(Kind="info", Message="Your bootloader will be updated or reinstalled in all Operating Systems it is installed in ("+', '.join(OSsForBootloaderRemoval)+"). Click okay to continue.")
                OSsForBootloaderInstallation = OSsForBootloaderRemoval[:]

            else: #*** Check all this works ***
                logger.info("HelperBackendTools: Main().AskUserForBootloaderInstallationOSs(): There is more than one Operating System with a supported package manager. Asking the user which ones to install the new bootloader in...")
                DialogTools.ShowMsgDlg(Kind="info", Message="Your bootloader will be removed in all Operating Systems it is installed in ("+', '.join(OSsForBootloaderRemoval)+"). You will now be asked which Operating Systems you want your new bootloader to be installed in.")

                #Make a list of candidates to install the bootloader in (only including OSes that will have their bootloaders removed).
                BootloaderCandidatesList = OSListWithPackageManagers[:]

                logger.debug("HelperBackendTools: Main().AskUserForBootloaderInstallationOSs(): Contents of BootloaderCandidatesList: "+', '.join(BootloaderCandidatesList))
                logger.info("HelperBackendTools: Main().AskUserForBootloaderInstallationOSs(): Asking the user which new OS to install the bootloader to...")

                #Ask the user which candidate(s) to use for bootloader installation. *** Is this bad advice? ***
                OSsForBootloaderInstallation = DialogTools.ShowMultiChoiceDlg(Message="Please select each OS you'd like to modify or install the bootloader to.\nIdeally, select the ones that you use most frequently.", Title="WxFixBoot - Select Operating Systems For Bootloader Installation", Choices=BootloaderCandidatesList)

                logger.info("HelperBackendTools: Main().AskUserForBootloaderInstallationOSs(): User selected: "+Result+"...")

        logger.info("HelperBackendTools: Main().AskUserForInstallationOSs(): Finished selecting OSs! Modifying or Installing the new bootloader in: "+', '.join(OSsForBootloaderInstallation))
        return OSsForBootloaderInstallation

    def FindBootloaderRemovalOSs(self, OSListWithPackageManagers, AutoRootFS, Bootloader): #*** Check this works ***
        """Find the OS(es) that currently have the bootloader installed, so we know where to remove it from."""
        logger.info("HelperBackendTools: Main().FindBootloaderRemovalOSs(): Looking for Operating Systems that currently have the bootloader installed, to add to the removal list...")
        #*** Temporarily define this as global until switch to dictionaries ***
        global OSsForBootloaderRemoval

        OSsForBootloaderRemoval = []

        for OS in OSListWithPackageManagers:
            #Grab the Package Manager and the partition the OS resides on. *** Keep this in the dictionary instead of having to do this kind of crap ***
            PackageManager = OS.split()[-1]
            Partition = OS.split()[-5]

            #Run some different instructions depending on whether the partition = AutoRootFS or not. *** Use a dictionary key to say which OS is the current one instead of doing this ***
            if SystemInfo["IsLiveDisk"] == False and Partition == AutoRootFS:
                UsingChroot = False
                MountPoint = "/"

            else:
                #Do some additional steps if we're using a live disk.
                MountPoint = "/mnt"+Partition
                UsingChroot = True

                #Mount the partition.
                Retval = CoreTools.MountPartition(Partition=Partition, MountPoint=MountPoint)

                #Check if anything went wrong.
                if Retval != 0:
                    #Ignore this partition.
                    logger.warning("HelperBackendTools: Main().FindBootloaderRemovalOSs(): Failed to mount "+Partition+"! Ignoring this partition...")
                    continue

                #Set up a chroot.
                CoreBackendTools.SetUpChroot(MountPoint=MountPoint)
                
            Found = self.LookForBootloaderOnPartition(Bootloader=Bootloader, PackageManager=PackageManager, MountPoint=MountPoint, UsingChroot=UsingChroot)

            if UsingChroot:
                #Tear down the chroot. #*** Check it worked! ***
                CoreBackendTools.TearDownChroot(MountPoint=MountPoint)

                #Unmount the partition.
                if CoreTools.Unmount(Partition) != 0:
                    logger.error("HelperBackendTools: Main().FindBootloaderRemovalOSs(): Failed to unmount "+Partition+"! Continuing anyway...")

            #Check if the bootloader was found on that partition. If it wasn't, don't do anything.
            if Found:
                #It was! Add it to the list.
                OSsForBootloaderRemoval.append(OS)
                logger.info("HelperBackendTools: Main().FindBootloaderRemovalOSs(): Found bootloader to remove: "+Bootloader+" On OS: "+OS+". Adding it to the list. Continuing...")

        #Return the list to self.PrepareForBootloaderInstallation()
        logger.info("HelperBackendTools: Main().FindBootloaderRemovalOSs(): Finished populating OSsForBootloaderRemoval. Contents: "+', '.join(OSsForBootloaderRemoval)+"...")
        return OSsForBootloaderRemoval

    def WriteFSTABEntryForUEFIPartition(self, MountPoint, UEFISystemPartition):
        """Write an /etc/fstab entry for the UEFI System Partition, if there isn't already one."""
        logger.info("HelperBackendTools: Main().WriteFSTABEntryForUEFIPartition(): Preparing to write an fstab entry for the UEFI partition ("+UEFISystemPartition+")...")

        WriteEntry = True

        #Make the directory MountPoint/boot/efi if it doesn't already exist.
        if os.path.isdir(MountPoint+"/boot/efi") == False:
            os.makedirs(MountPoint+"/boot/efi")

        #Get the UEFI System Partition's UUID. *** Will be in dictionary soon ***
        UUID = CoreBackendTools.GetPartitionUUID(UEFISystemPartition)

        #Open the MountPoint/etc/fstab file for reading. If we aren't using chroot, this'll just be /etc/fstab, otherwise, /mnt/dev/sdxy/etc/fstab. Also, save its contents in a variable.
        fstab = open(MountPoint+"/etc/fstab", "r")
        NewFileContents = []

        for line in fstab:
            if UEFISystemPartition in line or "UUID="+UUID in line:
                #This fstab already has an entry for the UEFI System Partition!
                WriteEntry = False

            NewFileContents.append(line)

        #Check if we need to write the entry.
        if WriteEntry == False:
            #We don't!
            logger.info("HelperBackendTools: Main().WriteFSTABEntryForUEFIPartition(): fstab entry already present! Skipping...")

        else:
            #We do. If we can use the UUID, then we will, but otherwise we'll use the standard device name.
            logger.info("HelperBackendTools: Main().WriteFSTABEntryForUEFIPartition(): Writing fstab entry...")
            NewFileContents.append("\n#fstab entry for UEFI System Partition (Partition "+UEFISystemPartition+"), written by WxFixBoot.\n")

            if UUID != "None":
                logger.info("HelperBackendTools: Main().WriteFSTABEntryForUEFIPartition(): Found UUID for UEFI Partition: "+UEFISystemPartition+". We'll use it to prevent problems down the line...")
                NewFileContents.append("UUID="+UUID+" /boot/efi vfat defaults 0 2\n")

            else:
                logger.warning("HelperBackendTools: Main().WriteFSTABEntryForUEFIPartition(): The UUID for the UEFI Partition: "+UEFISystemPartition+" couldn't be found! This isn't good, and may cause problems down the line. Continuing anyway, using device name instead...")
                NewFileContents.append(UEFISystemPartition+" /boot/efi vfat defaults 0 2\n")

            #Write the finished lines to the file.
            fstab.close()
            fstab = open(MountPoint+"/etc/fstab", 'w')
            fstab.write(''.join(NewFileContents))
            fstab.close()

            logger.info("HelperBackendTools: Main().WriteFSTABEntryForUEFIPartition(): Done!")

    def FindLatestVersion(self, Directory, Type):
        """Try the find the latest kernel/initrd in the given directory.""" #*** Would it be easier to use CoreTools.Find() and get rid of most of this? ***
        #Make a list of kerels/initrds.
        if Type == "Kernel":
            logger.info("HelperBackendTools: Main().FindLatestVersion(): Looking for latest kernel in "+Directory+"...")
            RegExp = r"(.*)vmlinuz(.*)"

        else:
            logger.info("HelperBackendTools: Main().FindLatestVersion(): Looking for latest initramfs in "+Directory+"...")
            RegExp = r"(.*)initrd(.*)"

        List = CoreTools.Find(Regexp, Directory)

        logger.debug("HelperBackendTools: Main().FindLatestVersion(): Contents of Kernel/Initrd list: "+', '.join(List))

        if len(List) == 0:
            #No kernels/initrds found.
            logger.warning("HelperBackendTools: Main().FindLatestVersion(): Found no Kernels/Initrds in "+Directory+"! This may indicate a bug in the program.") 
            return "None"

        elif len(List) == 1:
            #One kernel/initrd found, return it.
            logger.info("HelperBackendTools: Main().FindLatestVersion(): Found one Kernel/Initrd in "+Directory+"!") 
            return List[0]

        else:
            #Multiple kernels/initrds found!
            #Look for the one with highest version number, and if needed highest revision number.
            logger.info("HelperBackendTools: Main().FindLatestVersion(): Found multiple Kernels/Initrds in "+Directory+". Picking the newest one...")

            #while True:
            

            #Find the one with the highest version number.
            #Make a list of version numbers.
            Versions = []
            for Thing in List:
                Versions.append(Thing.split("-")[1])

            #Order them so that the last entry will have the latest version number.
            Versions = sorted(Versions, key=LooseVersion)

            #Save the kernel/initrd(s) that have the latest version number (the first element in the list).
            NewList = []
            for Thing in List:
                if Versions[-1] in Thing:
                    NewList.append(Thing)

            logger.debug("HelperBackendTools: Main().FindLatestVersion(): Contents of highest-version-number Kernel/Initrd list: "+', '.join(NewList))

            if len(NewList) == 1:
                #Good, there is only one kernel/initrd with that version number. Return it.
                logger.info("HelperBackendTools: Main().FindLatestVersion(): Found one Kernel/Initrd with the highest version number.")
                return NewList[0]

            else:
                #Multiple kernels/initrds with that version number.
                logger.info("HelperBackendTools: Main().FindLatestVersion(): Found multiple Kernels/Initrds with the highest version number! Picking the one with the highest revision number...")

                #Let's look at the revision number for every kernel/initrd in that list.
                Revs = []
                for Thing in NewList:
                    Revs.append(Thing.split("-")[2])

                #Order them so that the last entry will have the latest revision number.
                Revs = sorted(Revs, key=LooseVersion)

                #Save the kernels/initrd(s) that have that version number, and the latest revision number (the first element in the list).
                NewestList = []
                for Thing in NewList:
                    if Revs[-1] in Thing:
                        NewestList.append(Thing)

                logger.debug("HelperBackendTools: Main().FindLatestVersion(): Contents of highestrevision-number Kernel/Initrd list: "+', '.join(NewestList))

                if len(NewestList) == 1:
                    #Finally, we have the latest kernel/initrd! Return it.
                    logger.info("HelperBackendTools: Main().FindLatestVersion(): Yes! We found the latest Kernel/Initrd!")
                    return NewestList[0]

                else:
                    #Give up, this is getting impossible!
                    logger.error("HelperBackendTools: Main().FindLatestVersion(): Couldn't determine the newest kernel/Initrd! This is either because multple Kernels/Initrds have the highest revision number (!) or an error occoured when determining the revision number...")
                    return "None"

    def BackupUEFIFiles(self, MountPoint):
        """Backup some .efi files, just in case something goes wrong.""" #*** Make this more user friendly ***
        logger.info("HelperBackendTools: Main().BackupUEFIFiles(): Backing up UEFI Files...")

        #We'll backup /EFI/boot/bootx64.efi if it exists, and we'll also backup Windows's uefi files, if they exist.
        #First do /EFI/boot/bootx64.efi. Fortunately, the UEFI partition is always a fat32/fat16 filesystem, so case doesn't matter.
        logger.info("HelperBackendTools: Main().BackupUEFIFiles(): Backing up "+MountPoint+"/boot/efi/boot/boot*.efi...")
        if os.path.isfile(MountPoint+"/boot/efi/EFI/boot/boot*.efi"):
            retval = CoreTools.StartProcess("cp -v "+MountPoint+"/boot/efi/EFI/boot/boot*.efi "+MountPoint+"/boot/efi/EFI/boot/bkpbootx64.efi", ShowOutput=False)

        else:
            #This doesn't exist. This doesn't matter then, so set retval to 0.
            retval = 0

        #Check the return value.
        if retval != 0:
            logger.error("HelperBackendTools: Main().BackupUEFIFiles(): Failed to backup failsafe UEFI boot file! Warning user and continuing...")
            DialogTools.ShowMsgDlg(Kind="error", Message="Error! WxFixBoot failed to save your UEFI boot files to the backup directory! This probably isn't very important. Click okay to continue.")

        #Now do Windows's files, if they exist.
        logger.info("HelperBackendTools: Main().BackupUEFIFiles(): Backing up Windows's boot files if they exist...")
        if os.path.isfile(MountPoint+"/boot/efi/EFI/Microsoft/boot/bootmgfw.efi"):
            retval = CoreTools.StartProcess("cp -v "+MountPoint+"/boot/efi/EFI/Microsoft/boot/bootmgfw.efi "+MountPoint+"/boot/efi/EFI/Microsoft/boot/bkpbootmgfw.efi", ShowOutput=False)

        else:
            #They don't exist. This doesn't matter then, so set retval to 0.
            retval = 0

        logger.info("HelperBackendTools: Main().BackupUEFIFiles(): Done!")

        #Check the return value.
        if retval != 0:
            logger.error("HelperBackendTools: Main().BackupUEFIFiles(): Failed to backup Windows's UEFI boot files! Warning user and continuing...")
            DialogTools.ShowMsgDlg(Kind="error", Message="Warning: WxFixBoot failed to backup Windows's UEFI boot files! This probably isn't very important. Click okay to continue.")

    def CopyUEFIFiles(self, MountPoint):
        """Copy the new UEFI bootloader's files to default places in case of buggy firmware.""" #*** Lots of work needed here! Add more logging messages and error protection ***
        logger.info("HelperBackendTools: Main().CopyUEFIFiles(): Copying UEFI Files to UEFIBootDir...")

        #First, let's check if EFI/boot already exists. This is a fat32/fat16 filesystem, so case doesn't matter.
        if os.path.isdir(MountPoint+"/boot/efi/EFI/boot"):
            UEFIBootDir = MountPoint+"/boot/efi/EFI/boot"

        else:
            #It doesn't, so we'll create it.
            UEFIBootDir = MountPoint+"/boot/efi/EFI/boot"
            os.mkdir(UEFIBootDir)

        #Do it differently depending on whether the now-installed UEFI bootloader is ELILO or GRUB-UEFI.
        if BootloaderToInstall == "ELILO":
            #We need to copy both elilo.efi, and elilo.conf to UEFIBootDir.
            retval = CoreTools.StartProcess("cp -v "+MountPoint+"/boot/efi/EFI/ubuntu/elilo.efi "+UEFIBootDir+"/bootx64.efi", ShowOutput=False)
            retval = CoreTools.StartProcess("cp -v "+MountPoint+"/boot/efi/EFI/ubuntu/elilo.conf "+UEFIBootDir+"/", ShowOutput=False) #*** We're ignoring the last return value here! ***

        elif BootloaderToInstall == "GRUB-UEFI":
            #We need to copy grub*.efi to UEFIBootDir.
            retval = CoreTools.StartProcess("cp -v "+MountPoint+"/boot/efi/EFI/ubuntu/grub*.efi "+UEFIBootDir+"/bootx64.efi", ShowOutput=False)

        logger.info("HelperBackendTools: Main().CopyUEFIFiles(): Done!")

        #Check the return value. *** Not helpful to the user! ***
        if retval != 0:
            logger.error("HelperBackendTools: Main().CopyUEFIFiles(): Failed to copy the new bootloader's UEFI files to the failsafe directory! This could potentially be a serious problem! If the system doesn't start, this could be the reason why it doesn't start. Warning user and continuing...")
            DialogTools.ShowMsgDlg(Kind="error", Message="Error: WxFixBoot failed to copy the new bootloader's UEFI files to the backup directory! This could potentially be a problem. If your system doesn't start, this could be the reason why it doesn't start. Click okay to continue.")


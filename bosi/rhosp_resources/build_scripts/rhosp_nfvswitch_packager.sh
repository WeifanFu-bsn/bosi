#!/bin/bash -eux

# Following build params expected for this script:
# OpenStackBranch
# BcfBranch

# Revision is set to a constant 0. If ever this needs changing,
# it can be added to build params
Revision="0"

# mapping for OpenStackBranch to RHOSPVersion, default is latest = 9
# occasionally cleanup when we stop supporting certain versions
RHOSPVersion="9"
case "$OpenStackBranch" in
  *"mitaka"*) RHOSPVersion="9" ;;
  *"liberty"*) RHOSPVersion="8" ;;
  *"kilo"*) RHOSPVersion="7" ;;
esac

# if IvsBranch is not specified, it is same as BcfBranch
if [ -z "${IvsBranch+x}" ]; then
    IvsBranch="$BcfBranch"
fi

# cleanup old stuff
sudo rm -rf *

# get nfvswitch packages
mkdir nfvswitch
rsync -e 'ssh -o "StrictHostKeyChecking no"' -uva  bigtop:public_html/nfvswitch/centos7-x86_64/$IvsBranch/latest/* ./nfvswitch

# get nfvswitch-qemu packages
mkdir nfvswitch_qemu
rsync -e 'ssh -o "StrictHostKeyChecking no"' -uva  bigtop:public_html/rhosp_nfvswitch_qemu/* ./nfvswitch_qemu

# get bsnstacklib packages
mkdir bsnstacklib
rsync -e 'ssh -o "StrictHostKeyChecking no"' -uva  bigtop:public_html/bsnstacklib/centos7-x86_64/$OpenStackBranch/latest/* ./bsnstacklib

# get horizon-bsn packages
mkdir horizon-bsn
rsync -e 'ssh -o "StrictHostKeyChecking no"' -uva  bigtop:public_html/horizon-bsn/centos7-x86_64/$OpenStackBranch/latest/* ./horizon-bsn

# get bosi scripts
mkdir bosi
rsync -e 'ssh -o "StrictHostKeyChecking no"' -uva  bigtop:public_html/bosi/$BcfBranch/latest/* ./bosi

# grunt work aka packaging
mkdir tarball
# nfvswitch rpms
mv ./nfvswitch/nfvswitch-*.rpm ./tarball
# nfvswitch_qemu rpms
mv ./nfvswitch_qemu/* ./tarball
# BOSI contains these files namely: customize.sh  README  startup.sh
mv ./bosi/rhosp_resources/nfvswitch/* ./tarball
# Sample yaml files
mv ./bosi/rhosp_resources/yamls ./tarball
# bosi offline installation package
mv ./bosi/bosi_offline_packages_*tar.gz ./tarball
# bsnstacklib
mv ./bsnstacklib/*.noarch.rpm ./tarball
# horizon-bsn
mv ./horizon-bsn/*.noarch.rpm ./tarball

get_version () {
    RPM=$1;
    B=${RPM##*/};
    B=${B%-*};
    V=${B##*-};
}

# given $BcfBranch is master, IVS_VERSION will be whatever value set in master.
# hence we take it from package name
IVS_VERSION="$IvsBranch"
if [ "$IVS_VERSION" == "master" ]
then
    IVS_PKG="`ls ./tarball/ivs-debug*`"
    get_version $IVS_PKG
    IVS_VERSION=$V
fi

NFVSWITCH_VERSION="$IvsBranch"
if [ "$NFVSWITCH_VERSION" == "master" ]
then
    NFVSWITCH_PKG="`ls ./tarball/nfvswitch-debug*`"
    get_version $NFVSWITCH_PKG
    NFVSWITCH_VERSION=$V
fi

# bsnstacklib and horizon-bsn is <openstack-version>.<bcf-version>.<bug-fix-id>
# however, to maintain compatibility with lower version of bcf releases,
# $BcfBranch specified for build and latest package's <bcf-version> may not be same.
# e.g. liberty, 3.7 will still use liberty.36.x since liberty was first released with
# BCF 3.6.0 and we want to retain support

BSNLIB_PKG="`ls ./tarball/python-networking-bigswitch*`"
get_version $BSNLIB_PKG
BSNSTACKLIB_VERSION=$V

HORIZON_PKG="`ls ./tarball/python-horizon-bsn*`"
get_version $HORIZON_PKG
HORIZON_BSN_VERSION=$V

echo "nfvswitch version is" $NFVSWITCH_VERSION
echo "bsnstacklib version is" $BSNSTACKLIB_VERSION
echo "horizon-bsn version is" $HORIZON_BSN_VERSION

# IVS_VERSION_REVISION includes ivs version with its revision number, default = -1. redhat naming convention
# that needs to be adhered.
IVS_VERSION_REVISION="$IVS_VERSION""-1"
# for beta releases, revision is preappended, no changes required
# i.e. 4.0.0-beta1 already has revision set to beta1
if [[ "$IVS_VERSION" == *"beta"* ]]
then
    IVS_VERSION_REVISION="$IVS_VERSION"
fi

sed -i -e "s/\${bsnstacklib_version}/$BSNSTACKLIB_VERSION/" -e "s/\${horizon_bsn_version}/$HORIZON_BSN_VERSION/" -e "s/\${nfvswitch_version}/$NFVSWITCH_VERSION/" -e "s/\${ivs_version}/$IVS_VERSION_REVISION/" ./tarball/customize.sh
sed -i -e "s/\${bsnstacklib_version}/$BSNSTACKLIB_VERSION/" -e "s/\${horizon_bsn_version}/$HORIZON_BSN_VERSION/" -e "s/\${nfvswitch_version}/$NFVSWITCH_VERSION/" -e "s/\${ivs_version}/$IVS_VERSION_REVISION/" ./tarball/startup.sh
sed -i -e "s/\${bsnstacklib_version}/$BSNSTACKLIB_VERSION/" -e "s/\${horizon_bsn_version}/$HORIZON_BSN_VERSION/" -e "s/\${nfvswitch_version}/$NFVSWITCH_VERSION/" -e "s/\${ivs_version}/$IVS_VERSION_REVISION/" ./tarball/README

DATE=`date +%Y-%m-%d`
TAR_NAME="BCF-RHOSP-$RHOSPVersion-plugins-$NFVSWITCH_VERSION.$Revision-$DATE"
mv tarball $TAR_NAME
tar -zcvf $TAR_NAME.tar.gz $TAR_NAME

# Copy built tarball to pkg/
OUTDIR=$(readlink -m "pkg/$OpenStackBranch/$TAR_NAME")
rm -rf "$OUTDIR" && mkdir -p "$OUTDIR"
mv $TAR_NAME.tar.gz "$OUTDIR"
ln -snf $(basename $OUTDIR) $OUTDIR/../latest

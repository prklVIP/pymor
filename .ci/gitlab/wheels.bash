#!/bin/bash

set -e

if [[ "x${CI_COMMIT_TAG}" == "x" ]] ; then
    sed -i -e 's;style\ \=\ pep440;style\ \=\ ci_wheel_builder;g' setup.cfg
fi

set -u

# since we're in a d-in-d setup this needs to a be a path shared from the real host
BUILDER_WHEELHOUSE=${SHARED_PATH}
PYMOR_ROOT="$(cd "$(dirname ${BASH_SOURCE[0]})" ; cd ../../ ; pwd -P )"
cd "${PYMOR_ROOT}"

set -x
mkdir -p ${BUILDER_WHEELHOUSE}

BUILDER_IMAGE=pymor/wheelbuilder:py${PYVER}
docker pull ${BUILDER_IMAGE} 1> /dev/null
docker run --rm  -t -e LOCAL_USER_ID=$(id -u)  \
    -v ${BUILDER_WHEELHOUSE}:/io/wheelhouse \
    -v ${PYMOR_ROOT}:/io/pymor ${BUILDER_IMAGE} /usr/local/bin/build-wheels.sh #1> /dev/null

cp ${PYMOR_ROOT}/.ci/docker/deploy_checks/Dockerfile ${BUILDER_WHEELHOUSE}
for os in ${TEST_OS} ; do
    docker build --build-arg tag=${os} ${BUILDER_WHEELHOUSE}
done

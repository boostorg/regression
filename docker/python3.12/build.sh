#!/bin/bash

set -xe
image=cppalliance/boost_regression_docker:1
echo image is $image
docker build -t $image .
echo $?
# if [ "$?" = "0" ] ; then
#     docker push $image
# fi

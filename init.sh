#!/usr/bin/env bash
gcloud preview app run\
 ./app.yaml --admin-host=localhost:59001\
  --host=localhost:59101\
  --storage-path=./datastore

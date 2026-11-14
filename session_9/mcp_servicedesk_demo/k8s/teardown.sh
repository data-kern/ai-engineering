#!/usr/bin/env bash
# Delete everything the demo created (the namespace takes all of it, including the database disk).
kubectl delete namespace servicedesk --ignore-not-found

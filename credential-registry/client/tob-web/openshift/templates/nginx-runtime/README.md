# nginx-runtime

The `nginx-runtime` Dockerfile and OpenShift build configuration template (and settings) are included for use with local development; both Docker Compose and local OpenShift clusters.

The resulting image is used as the runtime image during the `angular-on-nginx` build

In the **Pathfinder** environemnt the `angular-on-nginx` build pulls in a pre-built copy of the `nginx-runtime` image.
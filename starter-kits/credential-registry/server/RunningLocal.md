# Running on OpenShift
This project uses the scripts found in [openshift-project-tools](https://github.com/BCDevOps/openshift-project-tools) to setup and maintain OpenShift environments (both local and hosted).  Refer to the [OpenShift Scripts](https://github.com/BCDevOps/openshift-project-tools/blob/master/bin/README.md) documentation for details.

These instructions assume:
* You have Git, Docker, and the OpenShift CLI installed on your system, and they are functioning correctly.  The recommended approach is to use either [Homebrew](https://brew.sh/) (MAC) or [Chocolatey](https://chocolatey.org/) (Windows) to install the required packages.
* You have followed the [OpenShift Scripts](https://github.com/BCDevOps/openshift-project-tools/blob/master/bin/README.md) environment setup instructions to install and configure the scripts for use on your system.
* You have forked and cloned a local working copy of this project's source code.
* You are using a reasonable shell.  A "reasonable shell" is obvious on Linux and Mac, and is assumed to be the git-bash shell on Windows.
* You are working from the top level `./openshift` directory for the project.

Good to have:
* A moderate to advanced knowledge of OpenShift. There are two good PDFs available from Red Hat and O'Reilly on [OpenShift for Developers](https://www.openshift.com/promotions/for-developers.html) and [DevOps with OpenShift](https://www.openshift.com/promotions/devops-with-openshift.html).

For the commands mentioned in these instructions, you can use the `-h` parameter for usage help and options information.

## Working with OpenShift

When working with openshift, commands are typically issued against the `server-project` pair to which you are currently connected.  Therefore, when you are working with multiple servers (local, and remote for instance) you should always be aware of your current context so you don't inadvertently issue a command against the wrong server and project.  Although you can login to more than one server at a time it's always a good idea to completely logout of one server before working on another.

The automation tools provided by `openshift-project-tools` hide some of these details from you, in that they perform project context switching automatically.  However, what they don't do is provide server context switching.  They assume you are aware of your server context and you have logged into the correct server.

Some useful commands to help you determine your current context:
* `oc whoami -c` - Lists your current server and user context.
* `oc project` - Lists your current project context.
* `oc project [NAME]` - Switch to a different project context.
* `oc projects` - Lists the projects available to you on the current server.

# Change into the top level openshift folder
```
cd /<PathToWorkingCopy>/openshift
```

# Getting Started Locally - oc cluster up
```
oc-cluster-up.sh
```
This will start your local OpenShift cluster using persistence so your configuration is preserved across restarts.

*To cleanly shutdown your local cluster use `oc-cluster-down.sh`.*

**Login** to your local OpenShift instance on the command line and the Web Console, using `developer` as both the username and password.  To login to the cluster from the command line, you can get a login token from the Web Console: Login to the console.  From the **?** dropdown select **Command Line Tools**.  Click on the **Copy To Clipboard** icon next to the `oc login` line.

# Create a local set of OpenShift projects
```
generateLocalProjects.sh
```
**This command will only work on a local server context.  It will fail if you are logged into a remote server.**  This will generate four OpenShift projects; tools, dev, test, and prod.  The tools project is used for builds and DevOps activities, and dev, test, and prod are a set of deployment environments.

If you need (or want) to reset your local environments you can run `generateLocalProjects.sh -D` to delete all of the OpenShift projects.

# Initialize the projects - add permissions and storage
```
initOSProjects.sh
```
This will initialize the projects with permissions that allow images from one project (tools) to be deployed into another project (dev, test, prod).  For production environments will also ensure the persistent storage services exist.

If you are running locally you will see some "No resources found." messages.  These can safely by ignored.

# Generate local parameters
When you are working with a local cluster you should generate a set of local param files.  This will ensure, at the very minimum, the CPU and Memory resources (limits and requests) are configured properly to avoid builds and deployments from hanging due to lack of sufficient resources.

To generate a set of local params, run;
```
genParams.sh -l
```
Local param files are ignored by Git, so you cannot accidentally commit them to the repository.

## Update the local parameters

### `angular-on-nginx-build.local.param`

The `openshift/nginx-runtime:latest` image that the angular-on-nginx build uses is not available to your local openshift cluster.

To solve this problem an nginx-runtime build configuration has been included in the project.  This build configuration will build an equivalent nginx-runtime image.

You will need to update `angular-on-nginx-build.local.param` to use the local version of the image, as follows;

Replace the line:
```
# RUNTIME_IMAGE_NAMESPACE=openshift
```

With:
```
# Use the locally built nginx-runtime image.
RUNTIME_IMAGE_NAMESPACE=
```

# Generate the Build and Images in the "tools" project; Deploy Jenkins
```
genBuilds.sh
```
This will generate and deploy the build configurations into the `tools` project.  Follow the instructions written to the command line.

If the project contains any Jenkins pipelines a Jenkins instance will be deployed into the `tools` project automatically once the first pipeline is deployed by the scripts.  OpenShift will automatically wire the Jenkins pipelines to Jenkins projects within Jenkins.

Use `-h` to get advanced usage information.  Use the `-l` option to apply any local settings you have configured; when working with a local cluster you should always use the `-l` option.

## Updating Build and Image Configurations
If you are adding build and image configurations you can re-run this script.  You will encounter errors for any of the resources that already exist, but you can safely ignore these errors and allow the script to continue.

If you are updating build and image configurations use the `-u` option.

If you are adding and updating build and image configurations, run the script **without** the `-u` option first to create the new resources and then again **with** the `-u` option to update the existing configurations.

# Generate the Deployment Configurations and Deploy the Components
```
genDepls.sh -e <EnvironmentName, one of [dev|test|prod]>
```
This will generate and deploy the deployment configurations into the selected project; `dev`, `test`, or `prod`.  Follow the instructions written to the command line.

Use `-h` to get advanced usage information.  Use the `-l` option to apply any local settings you have configured; when working with a local cluster you should always use the `-l` option.

## Updating Deployment Configurations

If you are adding deployment configurations you can re-run this script.  You will encounter errors for any of the resources that already exist, but you can safely ignore these errors and allow the script to continue.

If you are updating deployment configurations use the `-u` option.

If you are adding and updating deployment configurations, run the script **without** the `-u` option first to create the new resources and then again **with** the `-u` option to update the existing configurations.

**_Note;_**

**Some settings on some resources are immutable.  To replace these resources you will need to delete and recreate the associated resource(s).**

**Updating the deployment configurations can affect (overwrite) auto-generated secretes such as the database username and password.**

**Care must be taken with resources containing credentials or other auto-generated resources.  You must ensure such resources are replaced using the same values._**


# Fixing routes - Local Clusters
In the current instance of the deployment, the routes created are explicitly defined for the Pathfinder (BC Gov) instance of OpenShift. Run the following script to create the default routes for your local environment:
```
updateRoutes.sh
```

# Hangs, Corrections and Overrides
The generation of builds and deployments may hang because the environment on which you are running has fewer resources (especially less memory) than is requested in the templates. The scripts give you some guidance as to what you need to do to manually fix your current setup run.

Notably:
* Cancel the current action (build or deploy)
* Remove the resources settings in either the YAML (build config) or be clearing the fields in the "Resource Limits" screen (deployment config).

The scripts also have a mechanism to override default parameters that should allow you to eliminate these hangs from occurring in the first place.  The BuildConfig and DeploymentConfig overrides occur by setting values in template "param" files that override the defaults for the app. Refer to the `Generate local parameters` section for details.

# Loading Data

To load the test data into your instance of OpenShift, run:

```
loadData.sh
```

You should see a series of blocks of data and "201" return code. If you see errors messages, the data step had "challenges". Contact us with questions.

If the load data step fails, you can:

- go to the APISpec/TestData folder in the repository
- view and run the "load-all.sh" script. If you are loading data into the local environment, use an argument of "local"

NOTE: Data loads cannot be run multiple times. If you want to reload the data, you must first delete the database. You can do that by redeploying the entire environment, or going into Postgres and drop/recreating the database (instructions not yet available).
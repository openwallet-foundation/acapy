/**
  * This is the closure defining the main pipeline steps.
  * It will be executed when importing this file into another pipeline using 'load'.
  **/
{ ->
  node {
    stage('Checkout Source') {
      echo "Checking out source code ..."
      // Check out main source code
      checkout([
        $class: 'GitSCM',
        branches: [[name: "*/${TOB_SOURCE_REPO_BRANCH}"]],
        extensions: [
          [$class: 'RelativeTargetDirectory', relativeTargetDir: "${TOB_SOURCE_REPO_CHECKOUT_FOLDER}"]
        ],
        userRemoteConfigs: [[url: "${TOB_SOURCE_REPO}"]]
      ])

      if (TOB_THEME_REPO) {
        // We are using a custom theme, checkout the repository
        echo "Checking out custom theme source code from ${TOB_THEME_REPO}#${TOB_THEME_REPO_BRANCH}..."
        checkout([
          $class: 'GitSCM',
          branches: [[name: "*/${TOB_THEME_REPO_BRANCH}"]],
          extensions: [
            [$class: 'RelativeTargetDirectory', relativeTargetDir: "${TOB_THEME_REPO_CHECKOUT_FOLDER}"]
          ],
          userRemoteConfigs: [[url: "${TOB_THEME_REPO}"]]
        ])
      }
    }

    // build arifacts - binary source build
    stage("Build ${BUILD_CONFIG}") {
      withEnv([
        TOB_THEME_PATH = "${WORKSPACE}/custom-themes",
        TOB_THEME = "${TOB_THEME_NAME}"
        ]) {
          script {
            openshift.withCluster() {
              openshift.withProject() {

                echo "Building the application artifacts ..."
                def build = openshift.selector("bc", "${BUILD_CONFIG}")
                build.startBuild().logs("--from-dir='./credential-registry/tob-web' -f")
              }
            }
          }
        }
    }

    // Build the runtime image, if you are not using an off the shelf one.
    stage("Build ${RUNTIME_BUILD_CONFIG}") {
      script {
        openshift.withCluster() {
          openshift.withProject() {

            echo "Building the ${RUNTIME_BUILD_CONFIG} image ..."
            def build = openshift.selector("bc", "${RUNTIME_BUILD_CONFIG}")
            build.startBuild().logs("-f")
          }
        }
      }
    }

    stage("Build ${IMAGESTREAM_NAME}") {
      script {
        openshift.withCluster() {
          openshift.withProject() {

            echo "Building the ${IMAGESTREAM_NAME} image ..."
            def build = openshift.selector("bc", "${CHAINED_BUILD_CONFIG}")
            build.startBuild().logs("-f")
          }
        }
      }
    }

    stage("Deploy ${TAG_NAMES[0]}") {
      script {
        openshift.withCluster() {
          openshift.withProject() {

            echo "Tagging ${IMAGESTREAM_NAME} for deployment to ${TAG_NAMES[0]} ..."

            // Don't tag with BUILD_ID so the pruner can do it's job; it won't delete tagged images.
            // Tag the images for deployment based on the image's hash
            def IMAGE_HASH = getImageTagHash("${IMAGESTREAM_NAME}")
            echo "IMAGE_HASH: ${IMAGE_HASH}"
            openshift.tag("${IMAGESTREAM_NAME}@${IMAGE_HASH}", "${IMAGESTREAM_NAME}:${TAG_NAMES[0]}")
          }

          openshift.withProject("${DEV_NAME_SPACE}") {
              def dc = openshift.selector('dc', "${DEPLOYMENT_CONFIG_NAME}")
              // Wait for the deployment to complete.
              // This will wait until the desired replicas are all available
              dc.rollout().status()
          }

          echo "Deployment Complete."
        }
      }
    }

    stage('Trigger ZAP Scan') {
      script {
        openshift.withCluster() {
          openshift.withProject() {

            echo "Triggering an asynchronous ZAP Scan ..."
            def zapScan = openshift.selector("bc", "zap-pipeline")
            zapScan.startBuild()
          }
        }
      }
    }
}

/** These are utility functions and variables that can ONLY be used inside the pipeline,
  * they will NOT be available when loading this file inside another pipeline.
  **/

// Edit your app's name below
def APP_NAME = 'angular-app'

// Edit your environment TAG names below
def TAG_NAMES = ['dev', 'test', 'prod']

// You shouldn't have to edit these if you're following the conventions
def BUILD_CONFIG = "${APP_NAME}-build"

//EDIT LINE BELOW (Change `IMAGESTREAM_NAME` so it matches the name of your *output*/deployable image stream.)
def IMAGESTREAM_NAME = 'angular-on-nginx'

// you'll need to change this to point to your application component's folder within your repository
def CONTEXT_DIRECTORY = 'tob-web'

// EDIT LINE BELOW
// Add a reference to the RUNTIME_BUILD_CONFIG, if you are using a runtime that needs to be built.
// Otherwise comment out the line and the associated build script.
def RUNTIME_BUILD_CONFIG = 'nginx-runtime'

// EDIT LINE BELOW (Add a reference to the CHAINED_BUILD_CONFIG)
def CHAINED_BUILD_CONFIG = 'angular-on-nginx-build'

// The name of your deployment configuration; used to verify the deployment
def DEPLOYMENT_CONFIG_NAME = 'angular-on-nginx'

// The namespace of you dev deployment environment.
def DEV_NAME_SPACE = 'devex-von-dev'

@NonCPS
boolean triggerBuild(String contextDirectory) {
  // Determine if code has changed within the source context directory.
  def changeLogSets = currentBuild.changeSets
  def filesChangeCnt = 0
  for (int i = 0; i < changeLogSets.size(); i++) {
    def entries = changeLogSets[i].items
    for (int j = 0; j < entries.length; j++) {
      def entry = entries[j]
      def files = new ArrayList(entry.affectedFiles)
      for (int k = 0; k < files.size(); k++) {
        def file = files[k]
        def filePath = file.path
        if (filePath.contains(contextDirectory)) {
          filesChangeCnt = 1
          k = files.size()
          j = entries.length
        }
      }
    }
  }

  if ( filesChangeCnt < 1 ) {
    echo('The changes do not require a build.')
    return false
  }
  else {
    echo('The changes require a build.')
    return true
  }
}

// Get an image's hash tag
String getImageTagHash(String imageName, String tag = "") {

  if(!tag?.trim()) {
    tag = "latest"
  }

  def istag = openshift.raw("get istag ${imageName}:${tag} -o template --template='{{.image.dockerImageReference}}'")
  return istag.out.tokenize('@')[1].trim()
}

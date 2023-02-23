const path = require("path");
const fse = require("fs-extra");
const util = require("util");
const exec = util.promisify(require("child_process").exec);

const adminFiles = [
  "CHANGELOG.md",
  "CODE_OF_CONDUCT.md",
  "CONTRIBUTING.md",
  "MAINTAINERS.md",
  "PUBLISHING.md",
  "SECURITY.md",
];

const dirMapping = {
  "docs/assets": "docs/docs/assets",
  "docs/GettingStartedAriesDev": "developer",
  "docs/generated": "internal",
  "demo/collateral": "demo/collateral",
};

const rootPath = path.resolve(__dirname, "../..");
const docsPath = path.resolve(rootPath, "docs");
const docusaurusPath = path.resolve(rootPath, "docs/docusaurus/docs");
const assetsPath = path.resolve(rootPath, "docs/assets");
const developerPath = path.resolve(rootPath, "docs/GettingStartedAriesDev");
const demoPath = path.resolve(rootPath, "demo");
const demoCollateralPath = path.resolve(rootPath, "demo/collateral");
const rstPath = path.resolve(rootPath, "docs/generated");

/**
 * Steps:
 * - Build markdown files from docs/internal to docs/code
 * - Clean up generated code .md files
 * - Copy all .md|.png files from root to docs/docs
 * - Copy all files from docs/assets to docs/docs/assets
 * - Copy docs/GettingStartedAriesDev to docs/developer
 * - Copy all .md|.png files from demo to docs/demo
 * - Copy all .md|.png files from demo/collateral to docs/demo/collateral
 * - Copy docs/generated to docs/internal
 * - Copy all admin files in root to docs/admin
 */
async function main() {
  try {
    if (await fse.exists(docusaurusPath)) {
      await fse.remove(docusaurusPath);
    }

    // Build code docs
    await exec(
      `sphinx-build -b markdown -a -E -c ${docsPath} ${docsPath} ${path.resolve(
        docusaurusPath,
        "code"
      )}`
    );

    // Clean up code docs
    await fse.remove(path.resolve(docusaurusPath, "code", ".doctrees"));
    await fse.remove(path.resolve(docusaurusPath, "code", "docusaurus"));
    await fse.remove(path.resolve(docusaurusPath, "code", "rtd"));

    // Main docs
    await copyFiles(
      rootPath,
      path.resolve(docusaurusPath, "docs"),
      (file) =>
        !adminFiles.includes(file) &&
        (file.endsWith(".md") || file.endsWith(".png"))
    );

    // Main docs assets
    await copyFiles(
      assetsPath,
      path.resolve(docusaurusPath, dirMapping["docs/assets"]),
      (file) => file.endsWith(".md") || file.endsWith(".png")
    );

    // Developer docs
    await copyFiles(
      developerPath,
      path.resolve(docusaurusPath, dirMapping["docs/GettingStartedAriesDev"]),
      (file) => file.endsWith(".md") || file.endsWith(".png")
    );

    // Demo docs
    await copyFiles(
      demoPath,
      path.resolve(docusaurusPath, "demo"),
      (file) => file.endsWith(".md") || file.endsWith(".png")
    );

    // Demo docs assets
    await copyFiles(
      demoCollateralPath,
      path.resolve(docusaurusPath, dirMapping["demo/collateral"]),
      (file) => file.endsWith(".md") || file.endsWith(".png")
    );

    // Generated rst docs
    await copyFiles(
      rstPath,
      path.resolve(docusaurusPath, dirMapping["docs/generated"]),
      () => true
    );

    // Admin docs
    await copyFiles(rootPath, path.resolve(docusaurusPath, "admin"), (file) =>
      adminFiles.includes(file)
    );
  } catch (err) {
    console.error(err);
  }
}

async function copyFiles(from, to, filter) {
  try {
    const allFiles = await fse.readdir(from);
    const files = allFiles.filter(filter).map((file) => ({
      fromPath: path.resolve(from, file),
      toPath: path.resolve(rootPath, to, file),
    }));

    for ({ fromPath, toPath } of files) {
      await fse.copy(fromPath, toPath, { overwrite: true });
    }
  } catch (err) {
    console.error(err);
  }
}

main();

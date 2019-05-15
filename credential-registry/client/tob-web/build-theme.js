/**
 * Before building, files must be copied or symlinked into src/themes/_active
 * The default theme (src/themes/default) is always copied first, and then another
 * theme named by the TOB_THEME environment variable can add to or replace these files.
 **/

var fs = require('fs'),
  path = require('path');

var THEME_NAME = process.env.TOB_THEME || 'default';
if (THEME_NAME === '_active')
  throw 'Invalid theme name';
var THEME_PATH = process.env.TOB_THEME_PATH;
var TARGET_DIR = 'src/themes/_active';
var THEMES_ROOT = 'src/themes';
var LANG_ROOT = 'assets/i18n';
var CONFIG_NAME = 'assets/config.json';
var RESOLVE_LINKS = ['favicon.ico', 'styles.scss', LANG_ROOT, CONFIG_NAME];
var USE_LINKS = process.env.PREINSTALL_LINKS || false;
var UPDATE_ONLY = process.env.UPDATE_ONLY || false;
var REPLACE_VAR_PATHS = ['index.html', 'assets/bootstrap/manifest.json'];


if(! fs.copyFileSync) {
  // add stub for node.js versions before 8.5.0
  // NB: flags not implemented
  fs.copyFileSync = function(source, target, flags) {
    return fs.writeFileSync(target, fs.readFileSync(source));
  }
}

function unlinkRecursiveSync(dir) {
  if (fs.existsSync(dir)) {
    fs.readdirSync(dir).forEach(function(file, index) {
      var target_path = path.join(dir, file);
      if (fs.lstatSync(target_path).isDirectory()) {
        unlinkRecursiveSync(target_path);
      } else {
        fs.unlinkSync(target_path);
      }
    });
    fs.rmdirSync(dir);
  }
}

function populateDirSync(source_dir, target_dir) {
  fs.readdirSync(source_dir).forEach(function(file, index) {
    var source_path = path.join(source_dir, file);
    var target_path = path.join(target_dir, file);
    var source_stats = fs.lstatSync(source_path);
    var target_stats = null;
    try {
      target_stats = fs.lstatSync(target_path);
    } catch (err) { }
    if (target_stats && USE_LINKS && target_stats.isSymbolicLink()) {
      var sync_target_stats = fs.statSync(target_path);
      var resolved_source_path = fs.realpathSync(target_path);
      fs.unlinkSync(target_path);
      if (sync_target_stats.isDirectory()) {
        fs.mkdirSync(target_path);
        populateDirSync(resolved_source_path, target_path);
        target_stats = fs.lstatSync(target_path);
      } else {
        target_stats = null;
      }
    }

    if (target_stats) {
      if (target_stats.isDirectory()) {
        if (source_stats.isDirectory()) {
          populateDirSync(source_path, target_path);
          return;
        } else {
          unlinkRecursiveSync(target_path);
        }
      } else if (USE_LINKS) {
        fs.unlinkSync(target_path);
      }
    }

    if(! USE_LINKS) {
      if (source_stats.isDirectory()) {
        if (! target_stats) {
          fs.mkdirSync(target_path);
        }
        populateDirSync(source_path, target_path);
      } else {
        fs.copyFileSync(source_path, target_path);
      }
    } else {
      // must change to the target directory to create the relative symlink properly
      var link_path = path.relative(target_dir, source_path);
      var return_dir = path.relative(target_dir, process.cwd());
      process.chdir(target_dir);
      fs.symlinkSync(link_path, file);
      process.chdir(return_dir);
    }
  });
}

function copyThemeDir(theme_name, target_dir) {
  var theme_dir = path.join(THEMES_ROOT, theme_name);
  if (theme_name !== 'default') {
    theme_dir = path.join(THEME_PATH, theme_name);
  }
  try {
    fs.accessSync(theme_dir, fs.constants.F_OK);
  } catch (err) {
    throw `Theme directory not found:  ${theme_dir}`
  }
  try {
    fs.accessSync(theme_dir, fs.constants.R_OK);
  } catch (err) {
    throw `Theme directory not readable:  ${theme_dir}`
  }
  if (! fs.statSync(theme_dir).isDirectory()) {
    throw `Theme path is not a directory: ${theme_dir}`
  }
  populateDirSync(theme_dir, target_dir);
}

function cleanTargetDir(target_dir, root, depth) {
  if (!depth) depth = 0;
  try {
    fs.mkdirSync(target_dir);
  } catch (err) {
    if (err.code !== 'EEXIST') {
      throw err;
    }
  }
  fs.readdirSync(target_dir).forEach(function(file, index) {
    var target_path = path.join(root || '.', target_dir, file);
    var stat = fs.lstatSync(target_path);
    if (stat.isDirectory()) {
      cleanTargetDir(target_path, root, depth+1);
      fs.rmdirSync(target_path);
    } else if(stat.isSymbolicLink()) {
      fs.unlinkSync(target_path);
    } else {
      var del = ! USE_LINKS;
      if (!depth && ~RESOLVE_LINKS.indexOf(file)) {
        del = true;
      } else {
        var lang_path = path.join(TARGET_DIR, LANG_ROOT);
        if (target_path.startsWith(lang_path) && target_path.endsWith('.json')) {
          del = true;
        }
      }
      if (del) {
        fs.unlinkSync(target_path);
      } else {
        throw 'Non-symlinked file found in deployment directory, ' +
          'please move to themes directory or remove: ' + target_path;
      }
    }
  });
}

function resolveLinks(target_dir, paths) {
  // replace particular files that need to be copied, not symlinked
  if (!paths) return;
  for (var file of paths) {
    var target_path = path.join(target_dir, file);
    try {
      target_stats = fs.lstatSync(target_path);
    } catch (err) {
      continue;
    }
    if (target_stats.isSymbolicLink()) {
      var real_path = fs.realpathSync(target_path);
      var real_stats = null;
      fs.unlinkSync(target_path);
      try {
        real_stats = fs.lstatSync(real_path);
      } catch (err) {
        continue;
      }
      if(real_stats.isDirectory())
        fs.mkdirSync(target_path);
      else
        fs.copyFileSync(real_path, target_path);
    }
  }
}

function findLanguages(target_dir) {
  var ret = [];
  var lang_path = path.join(target_dir, LANG_ROOT);
  if (fs.existsSync(lang_path)) {
    fs.readdirSync(lang_path).forEach(function(file, index) {
      if(file.endsWith('.json')) {
        ret.push(file.substring(0, file.length - 5));
      }
    });
  }
  return ret;
}

function resolveLangPaths(theme_name, language) {
  var ret = [];
  if (THEME_PATH) {
    var lang_path = path.join(THEME_PATH, theme_name, LANG_ROOT, language + '.json');
    if (fs.existsSync(lang_path)) {
      ret.push(lang_path);
    }
  }
  if (theme_name !== 'default') {
    var def_path = path.join(THEMES_ROOT, 'default', LANG_ROOT, language + '.json');
    if (fs.existsSync(def_path)) {
      ret.push(def_path);
    }
  }
  if (language !== 'en') {
    ret = ret.concat(resolveLangPaths(theme_name, 'en'));
  }
  return ret;
}

function mergeDeep(target, ...sources) {
  if (!sources.length) return target;
  const source = sources.shift();
  if (typeof(target) === 'object' && typeof(source) === 'object') {
    for (const key in source) {
      if (typeof(source[key]) === 'object') {
        if (!target[key]) Object.assign(target, { [key]: {} });
        mergeDeep(target[key], source[key]);
      } else {
        Object.assign(target, { [key]: source[key] });
      }
    }
  }
  return mergeDeep(target, ...sources);
}

// merge theme and default language files
function combineLanguage(theme_name, target_dir) {
  var langs = new Array();
  if (THEME_PATH) {
    langs = findLanguages(path.join(THEME_PATH, theme_name));
  }
  if (theme_name !== 'default') {
    langs = langs.concat(findLanguages(path.join(THEMES_ROOT, 'default')));
  }
  var lang_dir = path.join(target_dir, LANG_ROOT);
  for (var lang of new Set(langs)) {
    var paths = resolveLangPaths(theme_name, lang);
    if (paths.length) {
      paths.reverse();
      var input = [];
      for (var lang_path of paths) {
        if(lang_path.startsWith(THEMES_ROOT)) {
          input.push(require('./' + lang_path));
        } else {
          input.push(require(lang_path));
        }
      }
      var data = mergeDeep(...input);
      if(! ('app' in data)) data['app'] = {};
      data['app']['theme-name'] = theme_name;
      var target_path = path.join(lang_dir, lang + '.json');
      var target_stats = null;
      try {
        target_stats = fs.lstatSync(target_path);
      } catch (err) {
      }
      if (target_stats && target_stats.isSymbolicLink()) {
        fs.unlinkSync(target_path);
      }
      fs.writeFileSync(target_path, JSON.stringify(data));
    }
  }
}

// combine theme config with default config
// and replace references to environment variables
function updateConfig(theme_name) {
  let source_path = path.join(THEMES_ROOT, theme_name, CONFIG_NAME);
  let default_path = path.join(THEMES_ROOT, 'default', CONFIG_NAME);
  let config = {};
  if (fs.existsSync(default_path)) {
    config = require('./' + default_path);
  }
  if (fs.existsSync(source_path)) {
    config = mergeDeep(config, require('./' + source_path));
  }
  let target_path = path.join(TARGET_DIR, CONFIG_NAME);
  let result = {};
  for(let k in config) {
    let v = config[k];
    result[k] = v.replace(/\$[A-Z_]+|\$\{.+?\}/g, (found) => {
      found = found.substring(1);
      if(found[0] === '{') found = found.substring(1, found.length - 1);
      let foundval = '';
      let splitPos = found.indexOf('-');
      if(~splitPos) {
        foundval = found.substring(splitPos + 1);
        found = found.substring(0, splitPos);
      }
      if(found == 'TOB_THEME')
        foundval = THEME_NAME;
      else if(found in process.env && process.env[found] !== '')
        foundval = process.env[found];
      return foundval;
    });
  }
  fs.writeFileSync(target_path, JSON.stringify(result));
  return result;
}

// replace variable references with values from (processed) config.json
function replaceVars(paths, config) {
  for(let replacePath of paths) {
    let sourcePath = path.join(TARGET_DIR, replacePath);
    if (fs.existsSync(sourcePath)) {
      let content = fs.readFileSync(sourcePath, 'utf8');
      content = content.replace(/\$\{[A-Z_]+\}/g, (found) => {
        found = found.substring(2, found.length - 1);
        return config[found] || '';
      });
      fs.writeFileSync(sourcePath, content);
    }
  }
}

if(UPDATE_ONLY) {
  console.log('Updating theme: %s', THEME_NAME);
}
else {
  console.log('Copying theme files to %s', TARGET_DIR);
  if(THEME_PATH){
    console.log('Custom theme directory: %s', THEME_PATH);
  }
  console.log('Theme selected: %s', THEME_NAME);
  cleanTargetDir(TARGET_DIR);
}

copyThemeDir('default', TARGET_DIR)
if (THEME_NAME !== 'default') {
  copyThemeDir(THEME_NAME, TARGET_DIR)
}

if(USE_LINKS)
  resolveLinks(TARGET_DIR, RESOLVE_LINKS);

combineLanguage(THEME_NAME, TARGET_DIR);

let CONFIG = updateConfig(THEME_NAME);
replaceVars(REPLACE_VAR_PATHS, CONFIG);

if(! UPDATE_ONLY)
  console.log('Done.\n');

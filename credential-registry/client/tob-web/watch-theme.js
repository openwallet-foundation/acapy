var childProcess = require('child_process');
var chokidar = require('chokidar');
var TOB_THEME = process.env.TOB_THEME || 'default';
var THEME_PATH = process.env.TOB_THEME_PATH || 'src/themes';


function runScript(scriptPath, options, callback) {
  // keep track of whether callback has been invoked to prevent multiple invocations
  var invoked = false;

  var proc = childProcess.fork(scriptPath, [], options);

  // listen for errors as they may prevent the exit event from firing
  proc.on('error', function (err) {
    if (invoked) return;
    invoked = true;
    callback(err);
  });

  // execute the callback once the process has finished running
  proc.on('exit', function (code) {
    if (invoked) return;
    invoked = true;
    var err = code === 0 ? null : new Error('exit code ' + code);
    callback(err);
  });
}

var watcher = chokidar.watch(['src/themes', THEME_PATH], {
  ignored: /^src\/themes\/_active(\/|$)/,
  ignoreInitial: true,
  persistent: true});

var running = false;

watcher.on('all', function(evt, path) {
  console.log('%s changed.', path);
  if(! running) {
    running = true;
    let updEnv = Object.assign({}, process.env, {TOB_THEME, UPDATE_ONLY: 'true'});
    runScript('build-theme.js', {env: updEnv}, function(err) {
      if (err) throw err;
      running = false;
      // console.log('finished running build-theme.js');
    });
  }
});

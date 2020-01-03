var createError = require('http-errors');
const express = require('express');
const path = require('path');
const cookieParser = require('cookie-parser');
const logger = require('morgan');
const exphbs = require('express-handlebars');
const helpers = require('handlebars-helpers');

const indexRouter = require('./routes/index');
const connectionRouter = require('./routes/connection');
const proofRouter = require('./routes/proof');

const app = express();

// view engine setup
app.set('views', path.join(__dirname, 'views'));
app.set('view engine', 'hbs');
app.engine('hbs', exphbs({
  extname: 'hbs',
  defaultView: 'default',
  layoutsDir: path.join(__dirname, '/views/layouts/'),
  partialsDir: [
    path.join(__dirname, '/views/partials'),
    path.join(__dirname, '/views/partials/connection'),
    path.join(__dirname, '/views/partials/home'),
    path.join(__dirname, '/views/partials/proof'),
  ],
  helpers: helpers(['array', 'comparison'])
}));

app.use(logger('dev'));
app.use(express.json());
app.use(express.urlencoded({ extended: false }));
app.use(cookieParser());
app.use(express.static(path.join(__dirname, 'public')));

app.use('/', indexRouter);
app.use('/connections', connectionRouter);
app.use('/proofs', proofRouter);

// catch 404 and forward to error handler
app.use(function(req, res, next) {
  next(createError(404));
});

// error handler
app.use(function(err, req, res, next) {
  // set locals, only providing error in development
  res.locals.message = err.message;
  res.locals.error = req.app.get('env') === 'development' ? err : {};

  // render the error page
  res.status(err.status || 500);
  res.render('error');
});

module.exports = app;

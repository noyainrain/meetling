// Karma configuration
// Generated on Fri May 12 2017 18:56:22 GMT+0200 (CEST)

module.exports = function(config) {
  config.set({

    frameworks: ['mocha'],

    // list of files / patterns to load in the browser
    files: [
        'node_modules/chai/chai.js',
        'meetling/res/static/micro/**/*.js'
    ],

    //reporters: ['dots'],

    // level of logging
    // possible values: config.LOG_DISABLE || config.LOG_ERROR || config.LOG_WARN || config.LOG_INFO || config.LOG_DEBUG
    //logLevel: config.LOG_INFO,

    // start these browsers
    // available browser launchers: https://npmjs.org/browse/keyword/karma-launcher
    browsers: ['Firefox'],
  })
}

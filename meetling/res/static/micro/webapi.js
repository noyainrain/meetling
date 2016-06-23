if (typeof exports === 'undefined') {
    // Browser
    var exports = micro.webapi;
} else {
    // Node.js
    var http = require('http');
    var url = require('url');
}

/**
 * TODO
 */
exports.WebAPIClient = function(url) {
    this.url = url;
};

Object.defineProperties(exports.WebAPIClient.prototype, {
    /**
     * Call a *method* on the HTTP JSON REST API endpoint at *url*.
     *
     * *method* is a HTTP method (e.g. ``GET`` or ``POST``). Arguments are passed as JSON object *args*.
     * A promise is returned that resolves to the result as JSON value, once the call is complete.
     *
     * If an error occurs, the promise rejects with an :class:`APIError`. For any IO related errors, it
     * rejects with a :class:`TypeError`.
     */
    call: {value: function(method, url, args) {
        var components = require('url').parse(this.url);
        var options = {
            protocol: components.protocol,
            hostname: components.hostname,
            port: components.port,
            method: method,
            path: components.path + url
        };

        if (args) {
            options.headers = {'Content-Type': 'application/json'};
        }

        return new Promise(function(resolve, reject) {
            var request = http.request(options, function(response) {
                // TODO: or do we have to reject with the error?
                if (response.statusCode > 500) {
                    throw new TypeError();
                }

                var body = '';
                response.setEncoding('utf8');
                response.on('data', function(data) {
                    body += data;
                });
                response.on('end', function() {
                    try {
                        var result = JSON.parse(body);
                    } catch(e) {
                        if (e instanceof SyntaxError) {
                            throw new TypeError();
                        } else {
                            throw e;
                        }
                    }

                    if (!(response.statusCode >= 200 && response.statusCode < 300)) {
                        //throw new exports.APIError(result, response.statusCode);
                        return reject(new exports.APIError(result, response.statusCode));
                    }
                    return resolve(result);
                });
            });
            request.end(JSON.stringify(args));
        });
    }}
});

/**
 * Thrown for HTTP JSON REST API errors.
 *
 * .. attribute:: error
 *
 *    The error object.
 *
 * .. attribute:: status
 *
 *    The associated HTTP status code.
 */
exports.APIError = function(error, status) {
    Error.call(this);
    this.error = error;
    this.status = status;
};

exports.APIError.prototype = Object.create(Error.prototype);

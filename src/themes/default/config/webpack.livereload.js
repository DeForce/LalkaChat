const LiveReloadPlugin = require('webpack-livereload-plugin');
const merge = require('webpack-merge');
const development = require('./webpack.development');

const livereload = {
    plugins: [
        new LiveReloadPlugin({
            port: 5000
        })
    ]
};

module.exports = merge(development, livereload);

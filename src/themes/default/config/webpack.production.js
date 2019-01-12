const merge = require('webpack-merge');
const common = require('./webpack.common');

const UglifyJsPlugin = require('webpack/lib/optimize/UglifyJsPlugin');
const NoErrorsPlugin = require('webpack/lib/NoErrorsPlugin');
const DefinePlugin = require('webpack/lib/DefinePlugin');

const production = {
    devtool: false,

    output: {
        filename: './js/[name].min.js'
    },

    plugins: [
        new NoErrorsPlugin(),

        new DefinePlugin({
            'process.env': {
                NODE_ENV: '"production"'
            }
        }),

//        new UglifyJsPlugin()
    ]
};

module.exports = merge(common, production);

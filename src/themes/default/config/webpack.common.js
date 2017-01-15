const CopyWebpackPlugin = require('copy-webpack-plugin');
const HtmlWebpackPlugin = require('html-webpack-plugin');

module.exports = {
    entry: {
        app: './app/app'
    },

    resolve: {
        extensions: ['', '.ts', '.js', '.json'],
        modulesDirectories: ['./node_modules', './app'],
        alias: {
            'vue$': 'vue/dist/vue.common.js'
        }
    },

    output: {
        path: './dist'
    },

    module: {
        loaders: [

        ]
    },

    plugins: [
        new CopyWebpackPlugin([
            { from: './assets' }
        ]),

        new HtmlWebpackPlugin({
            template: './assets/index.html',
            chunksSortMode: 'dependency',
            inject: 'body'
        })
    ]
};
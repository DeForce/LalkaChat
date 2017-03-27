const merge = require('webpack-merge');
const common = require('./webpack.common');

const development = {
    devtool: 'cheap-inline-source-map',
    output: {
        path: '../../../http/default',
        filename: './js/[name].js'
    }
};

module.exports = merge(common, development);

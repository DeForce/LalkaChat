const merge = require('webpack-merge');
const common = require('./webpack.common');

const development = {
    output: {
        filename: './js/[name].js'
    }
};

module.exports = merge(common, development);

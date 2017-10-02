const path = require('path');
const merge = require('webpack-merge');
const common = require('./common');
const { AotPlugin } = require('@ngtools/webpack');

const UglifyJsPlugin = require('webpack/lib/optimize/UglifyJsPlugin');
const { NoEmitOnErrorsPlugin, DefinePlugin } = require('webpack');

const dist = path.resolve(__dirname, '..', '..', 'dist');

const production = {
  devtool: false,

  output: {
    path: dist,
    filename: './js/[name].min.js'
  },

  plugins: [
    new DefinePlugin({
      PRODUCTION: JSON.stringify(true)
    }),

    new AotPlugin({
      mainPath: './src/main.ts',
      tsConfigPath: './tsconfig.json'
    }),

    new NoEmitOnErrorsPlugin(),

    new UglifyJsPlugin()
  ]
};

module.exports = merge(common, production);

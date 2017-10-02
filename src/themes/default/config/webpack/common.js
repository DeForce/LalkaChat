const path = require('path');
const CopyWebpackPlugin = require('copy-webpack-plugin');
const HtmlWebpackPlugin = require('html-webpack-plugin');

const entryPoints = ['polyfills', 'main'];

module.exports = {
  entry: {
    main: './src/main',
    polyfills: './src/polyfills'
  },

  resolve: {
    extensions: ['.ts', '.js', '.json'],
    modules: ['./node_modules', './src'],
  },

  output: {
    path: './dist'
  },
/*
  stats: {
    assets: false,
    cached: false,
    cachedAssets: false,
    children: false,
    chunks: false,
    chunkModules: false,
    chunkOrigins: false,
    colors: false,
    depth: false,
    entrypoints: false,
    errors: true,
    errorDetails: true,
    hash: false,
    maxModules: 0,
    modules: false,
    performance: false,
    providedExports: false,
    publicPath: false,
    reasons: false,
    source: false,
    timings: false,
    usedExports: false,
    version: false,
    warnings: false
  },
*/
  module: {
    rules: [
      {
        test: /\.html$/,
        loader: 'raw-loader'
      },
      {
        test: /\.ts$/,
        loader: '@ngtools/webpack'
      }
    ]
  },

  plugins: [
    new CopyWebpackPlugin([{ from: './src/assets' }]),

    new HtmlWebpackPlugin({
      template: './src/index.html',
      inject: 'body',
      chunksSortMode: (left, right) => {
        const [leftName] = left.names;
        const [rightName] = right.names;

        const leftIndex = entryPoints.indexOf(leftName);
        const rightindex = entryPoints.indexOf(rightName);

        return leftIndex > rightindex
          ? 1
          : -1;
      },
    })
  ],

  node: {
    fs: 'empty',
    crypto: 'empty',
    tls: 'empty',
    net: 'empty',
    global: true,
    process: true,
    module: false,
    clearImmediate: false,
    setImmediate: false
  },
};

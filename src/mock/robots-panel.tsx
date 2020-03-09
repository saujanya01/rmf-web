import React from 'react';
import ReactDOM from 'react-dom';
import RobotsPanel from '../components/robots-panel';
import fleets from './data/fleets';

ReactDOM.render(
  <RobotsPanel fleets={fleets} />,
  document.getElementById('root'),
);

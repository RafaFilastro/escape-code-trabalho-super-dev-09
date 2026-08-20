import { Routes } from '@angular/router';

import { Entrada } from './paginas/entrada/entrada';
import { Jogo } from './paginas/jogo/jogo';
import { Painel } from './paginas/painel/painel';
import { Resultado } from './paginas/resultado/resultado';
import { Falha } from './paginas/falha/falha';

export const routes: Routes = [
  {
    path: '',
    component: Entrada,
  },

  {
    path: 'jogo',
    component: Jogo,
  },

  {
    path: 'painel',
    component: Painel,
  },

  {
    path: 'resultado',
    component: Resultado,
  },

  {
    path: 'falha',
    component: Falha,
  },

  {
    path: '**',
    redirectTo: '',
  },
];

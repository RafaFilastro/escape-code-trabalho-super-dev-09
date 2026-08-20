import { ChangeDetectorRef, Component, OnInit } from '@angular/core';

import { FormsModule } from '@angular/forms';

import { HttpClient } from '@angular/common/http';

import { Router } from '@angular/router';

interface Partida {
  id: number;
  codigo: string;
  nome_protocolo: string;
  status: string;
  rodada_atual: number;
  quantidade_jogadores: number;
}

interface Jogador {
  id: number;
  partida_id: number;
  nome: string;
  pontuacao: number;
  rodadas_concluidas: number;
  finalizado: boolean;
}

@Component({
  selector: 'app-entrada',
  imports: [FormsModule],
  templateUrl: './entrada.html',
  styleUrl: './entrada.scss',
})
export class Entrada implements OnInit {
  private readonly apiUrl = 'http://127.0.0.1:8000';

  nome = '';

  partida: Partida | null = null;

  carregando = true;

  mensagemErro = '';

  constructor(
    private http: HttpClient,
    private router: Router,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit(): void {
    const mensagem = sessionStorage.getItem('mensagemEntrada');

    if (mensagem) {
      this.mensagemErro = mensagem;

      sessionStorage.removeItem('mensagemEntrada');
    }

    this.buscarPartidaAtiva();
  }

  buscarPartidaAtiva(): void {
    this.carregando = true;

    this.http.get<Partida>(`${this.apiUrl}/partidas/ativa`).subscribe({
      next: (partida) => {
        this.partida = partida;

        this.carregando = false;

        this.cdr.markForCheck();
      },

      error: () => {
        this.partida = null;

        this.carregando = false;

        this.cdr.markForCheck();
      },
    });
  }

  entrar(): void {
    const nomeLimpo = this.nome.trim();

    if (!nomeLimpo) {
      this.mensagemErro = 'Digite um codinome.';

      this.cdr.markForCheck();

      return;
    }

    if (!this.partida) {
      this.mensagemErro = 'Nenhuma operação disponível.';

      this.cdr.markForCheck();

      return;
    }

    if (this.partida.status !== 'AGUARDANDO') {
      this.mensagemErro = 'A operação já foi iniciada.';

      this.cdr.markForCheck();

      return;
    }

    this.mensagemErro = '';

    this.http
      .post<Jogador>(`${this.apiUrl}/jogadores`, {
        nome: nomeLimpo,

        codigo_partida: this.partida.codigo,
      })
      .subscribe({
        next: (jogador) => {
          /*
           * Uma nova operação sempre começa com
           * pontuação zerada para este codinome.
           *
           * O mesmo nome pode ser usado novamente
           * em outra partida.
           */
          localStorage.setItem('jogadorId', jogador.id.toString());

          localStorage.setItem('jogadorNome', jogador.nome);

          localStorage.setItem('partidaId', jogador.partida_id.toString());

          this.router.navigate(['/jogo']);
        },

        error: (erro) => {
          this.mensagemErro = erro.error?.detail ?? 'Não foi possível conectar ao sistema.';

          this.cdr.markForCheck();
        },
      });
  }

  textoStatus(): string {
    if (!this.partida) {
      return 'SEM OPERAÇÃO';
    }

    switch (this.partida.status) {
      case 'AGUARDANDO':
        return 'AGUARDANDO CODINOMES';

      case 'EM_ANDAMENTO':
        return 'CRIPTOGRAFIA EM CURSO';

      default:
        return this.partida.status;
    }
  }
}

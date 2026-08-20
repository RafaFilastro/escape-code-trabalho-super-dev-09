import { ChangeDetectorRef, Component, OnDestroy, OnInit } from '@angular/core';

import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Router } from '@angular/router';

interface JogadorResultado {
  posicao: number;
  id: number;
  nome: string;
  pontos: number;
}

interface DadosResultado {
  partida: {
    id: number;
    protocolo: string;
    status: string;
  };

  chave_mestre: string;

  fragmentos: string[];

  vencedor: JogadorResultado;

  ranking: JogadorResultado[];
}

@Component({
  selector: 'app-resultado',
  imports: [],
  templateUrl: './resultado.html',
  styleUrl: './resultado.scss',
})
export class Resultado implements OnInit, OnDestroy {
  progresso = 0;

  descriptografiaConcluida = false;

  intervalo: ReturnType<typeof setInterval> | null = null;

  partidaId = 0;

  chaveMestre = '';

  vencedor = {
    nome: 'AGUARDANDO',
    pontos: 0,
  };

  ranking: JogadorResultado[] = [];

  ehAdmin = false;

  criandoNovaPartida = false;

  mensagemAcao = '';

  constructor(
    private http: HttpClient,
    private router: Router,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit(): void {
    const partidaSalva =
      localStorage.getItem('partidaIdResultado') ?? localStorage.getItem('partidaId');

    this.partidaId = Number(partidaSalva);

    this.ehAdmin = !!sessionStorage.getItem('adminChave');

    this.buscarResultado();
  }

  ngOnDestroy(): void {
    this.pararIntervalo();
  }

  buscarResultado(): void {
    if (!this.partidaId) {
      console.log('ID da partida não encontrado para o resultado.');

      return;
    }

    this.http.get<DadosResultado>(`http://127.0.0.1:8000/resultados/${this.partidaId}`).subscribe({
      next: (dados) => {
        this.chaveMestre = dados.chave_mestre;

        this.vencedor = {
          nome: dados.vencedor.nome,
          pontos: dados.vencedor.pontos,
        };

        this.ranking = dados.ranking.slice(0, 5);

        this.cdr.markForCheck();

        this.iniciarDescriptografia();
      },

      error: (erro) => {
        console.log('Erro ao buscar resultado final:', erro);
      },
    });
  }

  iniciarDescriptografia(): void {
    this.pararIntervalo();

    this.progresso = 0;

    this.descriptografiaConcluida = false;

    this.cdr.markForCheck();

    this.intervalo = setInterval(() => {
      this.progresso += 2;

      if (this.progresso >= 100) {
        this.progresso = 100;

        this.descriptografiaConcluida = true;

        this.pararIntervalo();
      }

      this.cdr.markForCheck();
    }, 70);
  }

  irParaInicio(): void {
    localStorage.removeItem('jogadorId');

    localStorage.removeItem('jogadorNome');

    localStorage.removeItem('partidaId');

    localStorage.removeItem('partidaIdResultado');

    this.router.navigate(['/']);
  }

  criarNovoJogo(): void {
    const chaveAdmin = sessionStorage.getItem('adminChave');

    if (!chaveAdmin) {
      this.mensagemAcao = 'Acesso administrativo não encontrado.';

      this.cdr.markForCheck();

      return;
    }

    this.criandoNovaPartida = true;

    this.mensagemAcao = '';

    const headers = new HttpHeaders({
      'X-Admin-Key': chaveAdmin,
    });

    this.http
      .post(
        'http://127.0.0.1:8000/partidas',
        {},
        {
          headers: headers,
        },
      )
      .subscribe({
        next: () => {
          this.criandoNovaPartida = false;

          localStorage.removeItem('partidaIdResultado');

          this.router.navigate(['/painel']);
        },

        error: (erro) => {
          console.log('Erro ao criar novo jogo:', erro);

          this.criandoNovaPartida = false;

          this.mensagemAcao = erro.error?.detail ?? 'Não foi possível criar o novo jogo.';

          this.cdr.markForCheck();
        },
      });
  }

  pararIntervalo(): void {
    if (this.intervalo) {
      clearInterval(this.intervalo);

      this.intervalo = null;
    }
  }
}

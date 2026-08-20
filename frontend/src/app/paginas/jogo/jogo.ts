import { ChangeDetectorRef, Component, OnDestroy, OnInit } from '@angular/core';

import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';

interface Desafio {
  rodada: number;
  desafio_id: number;
  tema: string;
  pergunta: string;

  alternativas: {
    A: string;
    B: string;
    C: string;
    D: string;
    E: string;
  };

  alternativas_bloqueadas: string[];
}

interface UltimoTimeout {
  rodada: number;
  alternativa_correta: string;
  pontos_ganhos: number;
  fragmento_chave: string;
}

interface RelogioServidor {
  servidor_agora_ms: number;

  partida_inicia_em_ms: number | null;

  partida_termina_em_ms: number | null;

  rodada_inicia_em_ms: number | null;

  rodada_termina_em_ms: number | null;
}

interface EstadoJogador {
  jogador: {
    id: number;
    nome: string;
    pontuacao: number;
    rodadas_concluidas: number;
  };

  partida: {
    id: number;
    status: string;
    rodada_atual: number;
    duracao_rodada_segundos: number;
    segundos_partida: number;
    segundos_rodada: number;
  };

  relogio: RelogioServidor;

  aguardando_sincronizacao: boolean;

  desafio: Desafio | null;

  ultimo_timeout: UltimoTimeout | null;
}

interface RespostaServidor {
  correta: boolean;
  numero_tentativa: number;

  pontos_ganhos?: number;
  alternativa_bloqueada?: string;
  pontos_proxima_tentativa?: number;
  bloqueio_segundos?: number;
  fragmento_chave?: string;
  mensagem?: string;

  andamento?: {
    todos_concluiram: boolean;
    jogadores_prontos: number;
    total_jogadores: number;
    partida_finalizada: boolean;
    nova_rodada: number;
  };
}

@Component({
  selector: 'app-jogo',
  imports: [],
  templateUrl: './jogo.html',
  styleUrl: './jogo.scss',
})
export class Jogo implements OnInit, OnDestroy {
  private readonly apiUrl = 'http://127.0.0.1:8000';

  jogadorId = Number(localStorage.getItem('jogadorId'));

  jogadorNome = localStorage.getItem('jogadorNome') ?? 'CODINOME';

  desafio: Desafio | null = null;

  alternativasBloqueadas: string[] = [];

  aguardandoSincronizacao = false;

  bloqueadoPorErro = false;

  exibindoTimeout = false;

  respondendo = false;

  rodadaAtual = 0;

  tempoRodada = 20;

  tempoPartida = 0;

  duracaoRodada = 20;

  private desvioServidorMs = 0;

  private partidaTerminaEmMs: number | null = null;

  private rodadaIniciaEmMs: number | null = null;

  private rodadaTerminaEmMs: number | null = null;

  pontuacaoDisponivel = 1000;

  pontosGanhos = 0;

  fragmento = '';

  mensagem = '';

  alternativaCorretaTimeout = '';

  ultimaRodadaTimeoutExibida = 0;

  intervaloPolling: ReturnType<typeof setInterval> | null = null;

  intervaloRelogio: ReturnType<typeof setInterval> | null = null;

  timeoutBloqueio: ReturnType<typeof setTimeout> | null = null;

  constructor(
    private http: HttpClient,
    private router: Router,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit(): void {
    if (!this.jogadorId) {
      this.voltarParaEntrada('Sessão do codinome não encontrada.');

      return;
    }

    this.buscarEstado();

    /*
     * O servidor continua sendo consultado a cada 1 segundo
     * para estado, respostas, erros e avanço de rodada.
     *
     * O cronômetro NÃO depende mais desse intervalo.
     * Ele é redesenhado localmente usando o mesmo relógio
     * absoluto do servidor.
     */
    this.intervaloPolling = setInterval(() => {
      this.buscarEstado();
    }, 1000);

    this.intervaloRelogio = setInterval(() => {
      this.atualizarRelogiosLocais();
    }, 100);
  }

  ngOnDestroy(): void {
    if (this.intervaloPolling) {
      clearInterval(this.intervaloPolling);
    }

    if (this.intervaloRelogio) {
      clearInterval(this.intervaloRelogio);
    }

    if (this.timeoutBloqueio) {
      clearTimeout(this.timeoutBloqueio);
    }
  }

  get alternativas() {
    if (!this.desafio) {
      return [];
    }

    return [
      {
        letra: 'A',
        texto: this.desafio.alternativas.A,
      },
      {
        letra: 'B',
        texto: this.desafio.alternativas.B,
      },
      {
        letra: 'C',
        texto: this.desafio.alternativas.C,
      },
      {
        letra: 'D',
        texto: this.desafio.alternativas.D,
      },
      {
        letra: 'E',
        texto: this.desafio.alternativas.E,
      },
    ];
  }

  buscarEstado(): void {
    const enviadoEm = Date.now();

    this.http.get<EstadoJogador>(`${this.apiUrl}/jogadores/${this.jogadorId}/estado`).subscribe({
      next: (estado) => {
        const recebidoEm = Date.now();

        this.duracaoRodada = estado.partida.duracao_rodada_segundos;

        this.sincronizarRelogio(
          estado.relogio,
          enviadoEm,
          recebidoEm,
          estado.partida.segundos_partida,
          estado.partida.segundos_rodada,
        );

        if (estado.partida.status === 'FALHOU') {
          this.cancelarBloqueioErro();

          this.router.navigate(['/falha']);

          return;
        }

        /*
         * Mostra o timeout antes de seguir para a próxima
         * rodada ou para o resultado final.
         */
        if (
          estado.ultimo_timeout &&
          estado.ultimo_timeout.rodada > this.ultimaRodadaTimeoutExibida &&
          !this.exibindoTimeout
        ) {
          this.mostrarTimeout(estado.ultimo_timeout);

          return;
        }

        if (estado.partida.status === 'FINALIZADA') {
          this.cancelarBloqueioErro();

          localStorage.setItem('partidaIdResultado', estado.partida.id.toString());

          this.router.navigate(['/resultado']);

          return;
        }

        if (estado.partida.status === 'AGUARDANDO') {
          this.desafio = null;

          this.rodadaAtual = 0;

          this.aguardandoSincronizacao = true;

          this.mensagem = 'AGUARDANDO LIBERAÇÃO DO CONTROLADOR';

          this.cdr.markForCheck();

          return;
        }

        /*
         * ERRO:
         * durante os 2 segundos a pergunta não some do estado,
         * mas a interface fica travada e o polling não libera
         * os botões antes da hora.
         */
        if (this.bloqueadoPorErro || this.exibindoTimeout) {
          this.cdr.markForCheck();

          return;
        }

        const novaRodada = estado.partida.rodada_atual;

        if (novaRodada !== this.rodadaAtual) {
          this.rodadaAtual = novaRodada;

          this.pontuacaoDisponivel = 1000;

          this.pontosGanhos = 0;

          this.fragmento = '';

          this.mensagem = '';
        }

        /*
         * SINCRONIZAÇÃO PRINCIPAL:
         *
         * acertou antes dos outros?
         * -> fica aguardando.
         *
         * só sai quando o backend mudar rodada_atual,
         * ou seja, quando TODOS terminarem a rodada anterior.
         */
        this.aguardandoSincronizacao = estado.aguardando_sincronizacao;

        if (this.aguardandoSincronizacao) {
          this.desafio = null;

          this.mensagem = 'NÓ CONCLUÍDO // AGUARDANDO OS DEMAIS CODINOMES';

          this.cdr.markForCheck();

          return;
        }

        if (estado.desafio) {
          this.desafio = estado.desafio;

          this.alternativasBloqueadas = [...estado.desafio.alternativas_bloqueadas];

          const tentativaAtual = this.alternativasBloqueadas.length + 1;

          this.pontuacaoDisponivel = this.calcularPontuacao(tentativaAtual);
        } else {
          this.desafio = null;
        }

        this.cdr.markForCheck();
      },

      error: (erro) => {
        if (erro.status === 404) {
          this.voltarParaEntrada('Seu codinome foi removido. Cadastre-se novamente.');
        }
      },
    });
  }

  sincronizarRelogio(
    relogio: RelogioServidor,
    enviadoEm: number,
    recebidoEm: number,
    fallbackPartida: number,
    fallbackRodada: number,
  ): void {
    /*
     * Aproxima o instante em que a resposta passou
     * pelo servidor usando o ponto médio da requisição.
     *
     * Isso compensa boa parte da latência de rede.
     */
    const meioDaRequisicao = enviadoEm + (recebidoEm - enviadoEm) / 2;

    this.desvioServidorMs = relogio.servidor_agora_ms - meioDaRequisicao;

    this.partidaTerminaEmMs = relogio.partida_termina_em_ms;

    this.rodadaIniciaEmMs = relogio.rodada_inicia_em_ms;

    this.rodadaTerminaEmMs = relogio.rodada_termina_em_ms;

    /*
     * Fallback somente para estados que ainda não possuem
     * timestamp absoluto, como a sala aguardando início.
     */
    if (this.partidaTerminaEmMs === null) {
      this.tempoPartida = fallbackPartida;
    }

    if (this.rodadaTerminaEmMs === null) {
      this.tempoRodada = fallbackRodada;
    }

    this.atualizarRelogiosLocais();
  }

  atualizarRelogiosLocais(): void {
    const agoraServidor = Date.now() + this.desvioServidorMs;

    let mudou = false;

    if (this.partidaTerminaEmMs !== null) {
      const novoTempoPartida = Math.max(
        0,
        Math.ceil((this.partidaTerminaEmMs - agoraServidor) / 1000),
      );

      if (novoTempoPartida !== this.tempoPartida) {
        this.tempoPartida = novoTempoPartida;

        mudou = true;
      }
    }

    if (this.rodadaTerminaEmMs !== null) {
      let novoTempoRodada = this.duracaoRodada;

      /*
       * Entre uma rodada e outra o backend cria
       * uma pequena janela de sincronização.
       *
       * Enquanto o horário de início ainda não chegou,
       * todos continuam vendo exatamente 20 segundos.
       */
      if (this.rodadaIniciaEmMs !== null && agoraServidor >= this.rodadaIniciaEmMs) {
        novoTempoRodada = Math.max(
          0,
          Math.min(this.duracaoRodada, Math.ceil((this.rodadaTerminaEmMs - agoraServidor) / 1000)),
        );
      }

      if (novoTempoRodada !== this.tempoRodada) {
        this.tempoRodada = novoTempoRodada;

        mudou = true;
      }
    }

    if (mudou) {
      this.cdr.markForCheck();
    }
  }

  responder(alternativa: string): void {
    if (
      this.respondendo ||
      this.bloqueadoPorErro ||
      this.exibindoTimeout ||
      this.aguardandoSincronizacao ||
      this.alternativaBloqueada(alternativa)
    ) {
      return;
    }

    this.respondendo = true;

    this.http
      .post<RespostaServidor>(`${this.apiUrl}/respostas`, {
        jogador_id: this.jogadorId,

        rodada: this.desafio!.rodada,

        desafio_id: this.desafio!.desafio_id,

        alternativa: alternativa,
      })
      .subscribe({
        next: (resposta) => {
          this.respondendo = false;

          if (!resposta.correta) {
            const bloqueada = resposta.alternativa_bloqueada ?? alternativa;

            if (!this.alternativasBloqueadas.includes(bloqueada)) {
              this.alternativasBloqueadas.push(bloqueada);
            }

            this.pontuacaoDisponivel = resposta.pontos_proxima_tentativa ?? 200;

            this.mensagem = 'PACOTE CORROMPIDO';

            /*
             * O usuário fica 2 segundos sem poder tocar em nada.
             * Depois a mesma pergunta volta SOZINHA.
             */
            this.iniciarBloqueioErro();

            return;
          }

          this.pontosGanhos = resposta.pontos_ganhos ?? 0;

          this.fragmento = resposta.fragmento_chave ?? '';

          this.mensagem = 'NÓ DESCRIPTOGRAFADO';

          /*
           * Acertou:
           * vai imediatamente para a tela de espera.
           */
          this.aguardandoSincronizacao = true;

          this.desafio = null;

          this.cdr.markForCheck();

          /*
           * Se este foi o último jogador da rodada,
           * o backend já pode ter liberado a seguinte.
           */
          setTimeout(() => {
            this.buscarEstado();
          }, 350);
        },

        error: (erro) => {
          this.respondendo = false;

          /*
           * 409 significa que a resposta chegou depois
           * do encerramento da janela ou que a rodada
           * mudou enquanto o clique estava em trânsito.
           *
           * Não mostramos erro permanente: cancelamos
           * qualquer animação antiga e buscamos o estado
           * verdadeiro do servidor imediatamente.
           */
          if (erro.status === 409) {
            this.cancelarBloqueioErro();

            this.exibindoTimeout = false;

            this.mensagem = '';

            this.buscarEstado();

            this.cdr.markForCheck();

            return;
          }

          this.mensagem = erro.error?.detail ?? 'FALHA NA TRANSMISSÃO';

          this.cdr.markForCheck();
        },
      });
  }

  iniciarBloqueioErro(): void {
    this.bloqueadoPorErro = true;

    this.tocarSomErro();

    this.cdr.markForCheck();

    if (this.timeoutBloqueio) {
      clearTimeout(this.timeoutBloqueio);
    }

    this.timeoutBloqueio = setTimeout(() => {
      this.bloqueadoPorErro = false;

      this.timeoutBloqueio = null;

      this.mensagem = '';

      /*
       * Sem botão e sem clique:
       * ao terminar os 2 s busca novamente o mesmo estado.
       */
      this.buscarEstado();

      this.cdr.markForCheck();
    }, 2000);
  }

  cancelarBloqueioErro(): void {
    this.bloqueadoPorErro = false;

    this.respondendo = false;

    if (this.timeoutBloqueio) {
      clearTimeout(this.timeoutBloqueio);

      this.timeoutBloqueio = null;
    }
  }

  mostrarTimeout(timeout: UltimoTimeout): void {
    /*
     * CORREÇÃO DA CORRIDA ERRO x TIMEOUT:
     *
     * Antes, se o jogador errasse quando o relógio
     * estava acabando, o timeout chegava durante os
     * 2 segundos do efeito vermelho.
     *
     * mostrarTimeout limpava o setTimeout antigo,
     * porém `bloqueadoPorErro` continuava TRUE.
     * Depois a tela nunca mais saía do bloqueio.
     *
     * Agora o timeout encerra completamente o estado
     * de erro antes de assumir a interface.
     */
    this.cancelarBloqueioErro();

    this.exibindoTimeout = true;

    this.ultimaRodadaTimeoutExibida = timeout.rodada;

    this.alternativaCorretaTimeout = timeout.alternativa_correta;

    this.pontosGanhos = timeout.pontos_ganhos;

    this.fragmento = timeout.fragmento_chave;

    this.mensagem = 'TEMPO ESGOTADO';

    this.cdr.markForCheck();

    this.timeoutBloqueio = setTimeout(() => {
      this.exibindoTimeout = false;

      this.bloqueadoPorErro = false;

      this.timeoutBloqueio = null;

      this.aguardandoSincronizacao = true;

      /*
       * A rodada seguinte também aparece automaticamente.
       */
      this.buscarEstado();

      this.cdr.markForCheck();
    }, 2400);
  }

  alternativaBloqueada(letra: string): boolean {
    return this.alternativasBloqueadas.includes(letra);
  }

  calcularPontuacao(tentativa: number): number {
    if (tentativa === 1) {
      return 1000;
    }

    if (tentativa === 2) {
      return 800;
    }

    if (tentativa === 3) {
      return 600;
    }

    if (tentativa === 4) {
      return 400;
    }

    return 200;
  }

  textoTempoPartida(): string {
    const minutos = Math.floor(this.tempoPartida / 60);

    const segundos = this.tempoPartida % 60;

    return minutos.toString().padStart(2, '0') + ':' + segundos.toString().padStart(2, '0');
  }

  tocarSomErro(): void {
    try {
      const audio = new AudioContext();

      const agora = audio.currentTime;

      /*
       * Camada digital aguda.
       */
      const digital = audio.createOscillator();

      const ganhoDigital = audio.createGain();

      digital.type = 'square';

      digital.frequency.setValueAtTime(740, agora);

      digital.frequency.exponentialRampToValueAtTime(95, agora + 0.3);

      ganhoDigital.gain.setValueAtTime(0.065, agora);

      ganhoDigital.gain.exponentialRampToValueAtTime(0.001, agora + 0.34);

      digital.connect(ganhoDigital);

      ganhoDigital.connect(audio.destination);

      /*
       * Ruído curtíssimo para dar sensação
       * de pacote quebrado/glitch.
       */
      const duracao = 0.34;

      const buffer = audio.createBuffer(
        1,
        Math.floor(audio.sampleRate * duracao),
        audio.sampleRate,
      );

      const dados = buffer.getChannelData(0);

      for (let i = 0; i < dados.length; i++) {
        const envelope = 1 - i / dados.length;

        dados[i] = (Math.random() * 2 - 1) * envelope * (i % 5 === 0 ? 0.8 : 0.18);
      }

      const ruido = audio.createBufferSource();

      const filtro = audio.createBiquadFilter();

      const ganhoRuido = audio.createGain();

      ruido.buffer = buffer;

      filtro.type = 'highpass';

      filtro.frequency.value = 700;

      ganhoRuido.gain.setValueAtTime(0.045, agora);

      ganhoRuido.gain.exponentialRampToValueAtTime(0.001, agora + 0.34);

      ruido.connect(filtro);

      filtro.connect(ganhoRuido);

      ganhoRuido.connect(audio.destination);

      digital.start(agora);

      digital.stop(agora + 0.35);

      ruido.start(agora + 0.02);
    } catch {
      // O jogo continua mesmo se
      // o navegador bloquear áudio.
    }
  }

  voltarParaEntrada(mensagem: string): void {
    localStorage.removeItem('jogadorId');

    localStorage.removeItem('jogadorNome');

    localStorage.removeItem('partidaId');

    sessionStorage.setItem('mensagemEntrada', mensagem);

    this.router.navigate(['/']);
  }
}

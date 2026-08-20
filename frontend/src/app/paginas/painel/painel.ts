import { ChangeDetectorRef, Component, OnDestroy, OnInit } from '@angular/core';

import { FormsModule } from '@angular/forms';

import { HttpClient, HttpHeaders } from '@angular/common/http';

import { Router } from '@angular/router';

interface CodinomePainel {
  posicao: number;
  id: number;
  nome: string;
  pontuacao: number;
  sincronizado: boolean;
}

interface RelogioServidor {
  servidor_agora_ms: number;

  partida_inicia_em_ms: number | null;

  partida_termina_em_ms: number | null;

  rodada_inicia_em_ms: number | null;

  rodada_termina_em_ms: number | null;
}

interface DadosPainel {
  partida: {
    id: number;
    codigo: string;
    protocolo: string;
    status: string;
    rodada_atual: number;
    total_rodadas: number;
    duracao_rodada_segundos: number;
    segundos_restantes: number;
    segundos_rodada: number;
  };

  relogio: RelogioServidor;

  rodada: {
    jogadores_concluidos: number;
    total_jogadores: number;
    progresso: number;
    total_conclusoes: number;
  };

  descriptografia: {
    progresso: number;
    fragmentos: (string | null)[];
  };

  codinomios: CodinomePainel[];

  evento_erro: {
    ultimo_erro_id: number | null;

    ultimo_jogador: string | null;
  };
}

@Component({
  selector: 'app-painel',
  imports: [FormsModule],
  templateUrl: './painel.html',
  styleUrl: './painel.scss',
})
export class Painel implements OnInit, OnDestroy {
  private readonly apiUrl = 'http://127.0.0.1:8000';

  autenticado = false;

  chaveAdmin = '';

  carregandoAdmin = false;

  mensagemAdmin = '';

  semPartida = false;

  partidaIdAtual: number | null = null;

  codigoPartida = '';

  protocolo = '';

  statusPartida = '';

  rodadaAtual = 0;

  totalRodadas = 10;

  duracaoRodada = 20;

  segundosRestantes = 180;

  segundosRodada = 20;

  totalJogadores = 0;

  jogadoresConcluidos = 0;

  progressoRodada = 0;

  progressoGeral = 0;

  fragmentos: (string | null)[] = Array(10).fill(null);

  codinomios: CodinomePainel[] = [];

  painelTremendo = false;

  jogadorUltimoErro = '';

  private ultimoErroId: number | null = null;

  private erroMonitorInicializado = false;

  private totalConclusoesAnterior = 0;

  private primeiroCarregamento = true;

  private desvioServidorMs = 0;

  private partidaTerminaEmMs: number | null = null;

  private rodadaIniciaEmMs: number | null = null;

  private rodadaTerminaEmMs: number | null = null;

  private ultimoSegundoSonoro = -1;

  private ultimaRodadaSom = 0;

  private ultimoTimeoutSonoroRodada = 0;

  private intervaloPolling: ReturnType<typeof setInterval> | null = null;

  private intervaloRelogio: ReturnType<typeof setInterval> | null = null;

  private timeoutTremor: ReturnType<typeof setTimeout> | null = null;

  private audioContext: AudioContext | null = null;

  constructor(
    private http: HttpClient,
    private router: Router,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit(): void {
    const chaveSalva = sessionStorage.getItem('adminChave');

    if (chaveSalva) {
      this.chaveAdmin = chaveSalva;

      this.validarAcesso();
    }
  }

  ngOnDestroy(): void {
    if (this.intervaloPolling) {
      clearInterval(this.intervaloPolling);
    }

    if (this.intervaloRelogio) {
      clearInterval(this.intervaloRelogio);
    }

    if (this.timeoutTremor) {
      clearTimeout(this.timeoutTremor);
    }
  }

  headersAdmin(): HttpHeaders {
    return new HttpHeaders({
      'X-Admin-Key': this.chaveAdmin,
    });
  }

  validarAcesso(): void {
    const chave = this.chaveAdmin.trim();

    if (!chave) {
      this.mensagemAdmin = 'INFORME A CHAVE ADMINISTRATIVA';

      this.cdr.markForCheck();

      return;
    }

    this.chaveAdmin = chave;

    this.carregandoAdmin = true;

    this.mensagemAdmin = '';

    this.habilitarAudio();

    this.http
      .get(`${this.apiUrl}/admin/validar`, {
        headers: this.headersAdmin(),
      })
      .subscribe({
        next: () => {
          this.autenticado = true;

          this.carregandoAdmin = false;

          sessionStorage.setItem('adminChave', this.chaveAdmin);

          this.buscarPainel();

          this.iniciarAtualizacoes();

          this.cdr.markForCheck();
        },

        error: () => {
          this.autenticado = false;

          this.carregandoAdmin = false;

          this.mensagemAdmin = 'CHAVE ADMINISTRATIVA INVÁLIDA';

          this.cdr.markForCheck();
        },
      });
  }

  iniciarAtualizacoes(): void {
    if (this.intervaloPolling) {
      clearInterval(this.intervaloPolling);
    }

    if (this.intervaloRelogio) {
      clearInterval(this.intervaloRelogio);
    }

    /*
     * Estado do jogo:
     * consulta o servidor a cada 1 segundo.
     */
    this.intervaloPolling = setInterval(() => {
      this.buscarPainel();
    }, 1000);

    /*
     * Cronômetro:
     * desenhado localmente a cada 100 ms,
     * mas sempre baseado nos timestamps absolutos
     * enviados pelo servidor.
     */
    this.intervaloRelogio = setInterval(() => {
      this.atualizarRelogiosLocais();
    }, 100);
  }

  buscarPainel(): void {
    if (!this.autenticado) {
      return;
    }

    const enviadoEm = Date.now();

    this.http
      .get<DadosPainel>(`${this.apiUrl}/painel/partida-atual`, {
        headers: this.headersAdmin(),
      })
      .subscribe({
        next: (dados) => {
          const recebidoEm = Date.now();

          this.semPartida = false;

          const rodadaAnterior = this.rodadaAtual;

          this.partidaIdAtual = dados.partida.id;

          this.codigoPartida = dados.partida.codigo;

          this.protocolo = dados.partida.protocolo;

          this.statusPartida = dados.partida.status;

          this.rodadaAtual = dados.partida.rodada_atual;

          this.totalRodadas = dados.partida.total_rodadas;

          this.duracaoRodada = dados.partida.duracao_rodada_segundos;

          this.totalJogadores = dados.rodada.total_jogadores;

          this.jogadoresConcluidos = dados.rodada.jogadores_concluidos;

          this.progressoRodada = dados.rodada.progresso;

          this.progressoGeral = dados.descriptografia.progresso;

          this.fragmentos = dados.descriptografia.fragmentos;

          this.codinomios = dados.codinomios;

          if (rodadaAnterior !== this.rodadaAtual) {
            this.ultimoSegundoSonoro = -1;

            this.ultimaRodadaSom = this.rodadaAtual;
          }

          this.sincronizarRelogio(
            dados.relogio,
            enviadoEm,
            recebidoEm,
            dados.partida.segundos_restantes,
            dados.partida.segundos_rodada,
          );

          this.processarErroRemoto(dados.evento_erro);

          this.processarConclusoes(dados.rodada.total_conclusoes);

          if (this.statusPartida === 'FINALIZADA') {
            localStorage.setItem('partidaIdResultado', dados.partida.id.toString());

            this.router.navigate(['/resultado']);

            return;
          }

          if (this.statusPartida === 'FALHOU') {
            this.router.navigate(['/falha']);

            return;
          }

          this.cdr.markForCheck();
        },

        error: (erro) => {
          if (erro.status === 404) {
            this.semPartida = true;

            this.partidaIdAtual = null;

            this.codinomios = [];

            this.totalJogadores = 0;

            this.cdr.markForCheck();
          }

          if (erro.status === 401) {
            this.sairPainel();
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
     * O midpoint compensa parte do tempo gasto
     * na ida e volta da requisição.
     */
    const meioDaRequisicao = enviadoEm + (recebidoEm - enviadoEm) / 2;

    this.desvioServidorMs = relogio.servidor_agora_ms - meioDaRequisicao;

    this.partidaTerminaEmMs = relogio.partida_termina_em_ms;

    this.rodadaIniciaEmMs = relogio.rodada_inicia_em_ms;

    this.rodadaTerminaEmMs = relogio.rodada_termina_em_ms;

    if (this.partidaTerminaEmMs === null) {
      this.segundosRestantes = fallbackPartida;
    }

    if (this.rodadaTerminaEmMs === null) {
      this.segundosRodada = fallbackRodada;
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

      if (novoTempoPartida !== this.segundosRestantes) {
        this.segundosRestantes = novoTempoPartida;

        mudou = true;
      }
    }

    if (this.rodadaTerminaEmMs !== null) {
      let novoTempoRodada = this.duracaoRodada;

      if (this.rodadaIniciaEmMs !== null && agoraServidor >= this.rodadaIniciaEmMs) {
        novoTempoRodada = Math.max(
          0,
          Math.min(this.duracaoRodada, Math.ceil((this.rodadaTerminaEmMs - agoraServidor) / 1000)),
        );
      }

      if (novoTempoRodada !== this.segundosRodada) {
        this.segundosRodada = novoTempoRodada;

        mudou = true;

        this.processarSomDoCronometro(novoTempoRodada);
      }
    }

    if (mudou) {
      this.cdr.markForCheck();
    }
  }

  processarSomDoCronometro(segundos: number): void {
    if (this.statusPartida !== 'EM_ANDAMENTO' || this.rodadaAtual <= 0) {
      return;
    }

    if (this.ultimaRodadaSom !== this.rodadaAtual) {
      this.ultimaRodadaSom = this.rodadaAtual;

      this.ultimoSegundoSonoro = -1;
    }

    if (segundos >= 1 && segundos <= 5 && segundos !== this.ultimoSegundoSonoro) {
      this.ultimoSegundoSonoro = segundos;

      this.tocarPulsoCritico(segundos);
    }

    if (segundos === 0 && this.ultimoTimeoutSonoroRodada !== this.rodadaAtual) {
      this.ultimoTimeoutSonoroRodada = this.rodadaAtual;

      this.tocarSomTimeoutHacker();
    }
  }

  processarConclusoes(totalConclusoes: number): void {
    if (this.primeiroCarregamento) {
      this.totalConclusoesAnterior = totalConclusoes;

      this.primeiroCarregamento = false;

      return;
    }

    if (totalConclusoes > this.totalConclusoesAnterior) {
      this.tocarSomConclusao();
    }

    this.totalConclusoesAnterior = totalConclusoes;
  }

  processarErroRemoto(evento: DadosPainel['evento_erro']): void {
    if (!this.erroMonitorInicializado) {
      this.ultimoErroId = evento.ultimo_erro_id;

      this.erroMonitorInicializado = true;

      return;
    }

    if (evento.ultimo_erro_id === null || evento.ultimo_erro_id === this.ultimoErroId) {
      return;
    }

    this.ultimoErroId = evento.ultimo_erro_id;

    this.jogadorUltimoErro = evento.ultimo_jogador ?? 'CODINOME';

    this.dispararTremorErro();
  }

  dispararTremorErro(): void {
    this.painelTremendo = true;

    this.tocarSomErroRemoto();

    if (this.timeoutTremor) {
      clearTimeout(this.timeoutTremor);
    }

    this.timeoutTremor = setTimeout(() => {
      this.painelTremendo = false;

      this.cdr.markForCheck();
    }, 720);

    this.cdr.markForCheck();
  }

  criarNovaPartida(): void {
    this.http
      .post(
        `${this.apiUrl}/partidas`,
        {},
        {
          headers: this.headersAdmin(),
        },
      )
      .subscribe({
        next: () => {
          this.semPartida = false;

          this.primeiroCarregamento = true;

          this.erroMonitorInicializado = false;

          this.ultimoErroId = null;

          this.buscarPainel();
        },

        error: (erro) => {
          this.mensagemAdmin = erro.error?.detail ?? 'FALHA AO CRIAR OPERAÇÃO';

          this.cdr.markForCheck();
        },
      });
  }

  iniciarPartida(): void {
    if (this.partidaIdAtual === null) {
      return;
    }

    if (this.totalJogadores === 0) {
      this.mensagemAdmin = 'AGUARDE AO MENOS UM CODINOME';

      this.cdr.markForCheck();

      return;
    }

    this.habilitarAudio();

    this.http
      .post(
        `${this.apiUrl}/partidas/${this.partidaIdAtual}/iniciar`,
        {},
        {
          headers: this.headersAdmin(),
        },
      )
      .subscribe({
        next: () => {
          this.mensagemAdmin = '';

          this.buscarPainel();
        },

        error: (erro) => {
          this.mensagemAdmin = erro.error?.detail ?? 'FALHA AO INICIAR MISSÃO';

          this.cdr.markForCheck();
        },
      });
  }

  removerJogador(jogador: CodinomePainel): void {
    if (this.statusPartida !== 'AGUARDANDO') {
      return;
    }

    const confirmou = window.confirm('Remover o codinome ' + `"${jogador.nome}"?`);

    if (!confirmou) {
      return;
    }

    this.http
      .delete(`${this.apiUrl}/jogadores/${jogador.id}`, {
        headers: this.headersAdmin(),
      })
      .subscribe({
        next: () => {
          this.buscarPainel();
        },

        error: (erro) => {
          this.mensagemAdmin = erro.error?.detail ?? 'FALHA AO REMOVER CODINOME';

          this.cdr.markForCheck();
        },
      });
  }

  textoStatus(): string {
    switch (this.statusPartida) {
      case 'AGUARDANDO':
        return 'AGUARDANDO CODINOMES';

      case 'EM_ANDAMENTO':
        return 'CRIPTOGRAFIA EM CURSO';

      case 'FINALIZADA':
        return 'NÚCLEO DESCRIPTOGRAFADO';

      case 'FALHOU':
        return 'PROTOCOLO ZERO';

      default:
        return 'SEM SINAL';
    }
  }

  textoTempo(): string {
    const minutos = Math.floor(this.segundosRestantes / 60);

    const segundos = this.segundosRestantes % 60;

    return minutos.toString().padStart(2, '0') + ':' + segundos.toString().padStart(2, '0');
  }

  habilitarAudio(): void {
    try {
      if (!this.audioContext) {
        this.audioContext = new AudioContext();
      }

      if (this.audioContext.state === 'suspended') {
        this.audioContext.resume();
      }
    } catch {
      this.audioContext = null;
    }
  }

  tocarPulsoCritico(segundos: number): void {
    if (!this.audioContext) {
      return;
    }

    const audio = this.audioContext;

    const agora = audio.currentTime;

    const oscilador = audio.createOscillator();

    const ganho = audio.createGain();

    const frequencia = 330 + (5 - segundos) * 95;

    oscilador.type = 'square';

    oscilador.frequency.setValueAtTime(frequencia, agora);

    ganho.gain.setValueAtTime(0.032, agora);

    ganho.gain.exponentialRampToValueAtTime(0.001, agora + 0.09);

    oscilador.connect(ganho);

    ganho.connect(audio.destination);

    oscilador.start(agora);

    oscilador.stop(agora + 0.1);
  }

  tocarSomTimeoutHacker(): void {
    if (!this.audioContext) {
      return;
    }

    const audio = this.audioContext;

    const agora = audio.currentTime;

    const chirp = audio.createOscillator();

    const ganhoChirp = audio.createGain();

    chirp.type = 'square';

    chirp.frequency.setValueAtTime(1450, agora);

    chirp.frequency.exponentialRampToValueAtTime(170, agora + 0.34);

    ganhoChirp.gain.setValueAtTime(0.065, agora);

    ganhoChirp.gain.exponentialRampToValueAtTime(0.001, agora + 0.38);

    chirp.connect(ganhoChirp);

    ganhoChirp.connect(audio.destination);

    const impacto = audio.createOscillator();

    const ganhoImpacto = audio.createGain();

    impacto.type = 'sawtooth';

    impacto.frequency.setValueAtTime(115, agora + 0.18);

    impacto.frequency.exponentialRampToValueAtTime(34, agora + 0.78);

    ganhoImpacto.gain.setValueAtTime(0.001, agora);

    ganhoImpacto.gain.setValueAtTime(0.1, agora + 0.18);

    ganhoImpacto.gain.exponentialRampToValueAtTime(0.001, agora + 0.82);

    impacto.connect(ganhoImpacto);

    ganhoImpacto.connect(audio.destination);

    chirp.start(agora);

    chirp.stop(agora + 0.4);

    impacto.start(agora + 0.18);

    impacto.stop(agora + 0.84);
  }

  tocarSomConclusao(): void {
    if (!this.audioContext) {
      return;
    }

    const audio = this.audioContext;

    const agora = audio.currentTime;

    [520, 780, 1040].forEach((frequencia, indice) => {
      const oscilador = audio.createOscillator();

      const ganho = audio.createGain();

      const inicio = agora + indice * 0.065;

      oscilador.type = indice === 2 ? 'sine' : 'square';

      oscilador.frequency.setValueAtTime(frequencia, inicio);

      ganho.gain.setValueAtTime(0.04, inicio);

      ganho.gain.exponentialRampToValueAtTime(0.001, inicio + 0.12);

      oscilador.connect(ganho);

      ganho.connect(audio.destination);

      oscilador.start(inicio);

      oscilador.stop(inicio + 0.13);
    });
  }

  tocarSomErroRemoto(): void {
    if (!this.audioContext) {
      return;
    }

    const audio = this.audioContext;

    const agora = audio.currentTime;

    const oscilador = audio.createOscillator();

    const ganho = audio.createGain();

    oscilador.type = 'sawtooth';

    oscilador.frequency.setValueAtTime(240, agora);

    oscilador.frequency.exponentialRampToValueAtTime(58, agora + 0.28);

    ganho.gain.setValueAtTime(0.05, agora);

    ganho.gain.exponentialRampToValueAtTime(0.001, agora + 0.31);

    oscilador.connect(ganho);

    ganho.connect(audio.destination);

    oscilador.start(agora);

    oscilador.stop(agora + 0.32);
  }

  sairPainel(): void {
    if (this.intervaloPolling) {
      clearInterval(this.intervaloPolling);

      this.intervaloPolling = null;
    }

    if (this.intervaloRelogio) {
      clearInterval(this.intervaloRelogio);

      this.intervaloRelogio = null;
    }

    sessionStorage.removeItem('adminChave');

    this.autenticado = false;

    this.chaveAdmin = '';

    this.cdr.markForCheck();
  }
}

import { ChangeDetectorRef, Component, OnDestroy, OnInit } from '@angular/core';

import { HttpClient, HttpHeaders } from '@angular/common/http';

import { Router } from '@angular/router';

@Component({
  selector: 'app-falha',
  imports: [],
  templateUrl: './falha.html',
  styleUrl: './falha.scss',
})
export class Falha implements OnInit, OnDestroy {
  private readonly apiUrl = 'http://127.0.0.1:8000';

  ehAdmin = !!sessionStorage.getItem('adminChave');

  contador = 10;

  destruido = false;

  intervalo: ReturnType<typeof setInterval> | null = null;

  timeout: ReturnType<typeof setTimeout> | null = null;

  audioContext: AudioContext | null = null;

  constructor(
    private http: HttpClient,
    private router: Router,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit(): void {
    if (this.ehAdmin) {
      this.prepararAudio();

      this.iniciarProtocoloZero();
    } else {
      this.timeout = setTimeout(() => {
        this.destruido = true;

        this.cdr.markForCheck();
      }, 2800);
    }
  }

  ngOnDestroy(): void {
    if (this.intervalo) {
      clearInterval(this.intervalo);
    }

    if (this.timeout) {
      clearTimeout(this.timeout);
    }
  }

  iniciarProtocoloZero(): void {
    this.intervalo = setInterval(() => {
      this.contador -= 1;

      this.tocarAlerta();

      if (this.contador <= 0) {
        this.contador = 0;

        this.destruido = true;

        this.tocarImpactoFinal();

        if (this.intervalo) {
          clearInterval(this.intervalo);
        }
      }

      this.cdr.markForCheck();
    }, 1000);
  }

  prepararAudio(): void {
    try {
      this.audioContext = new AudioContext();

      if (this.audioContext.state === 'suspended') {
        this.audioContext.resume();
      }
    } catch {
      this.audioContext = null;
    }
  }

  tocarAlerta(): void {
    if (!this.audioContext) {
      return;
    }

    const audio = this.audioContext;

    if (audio.state === 'suspended') {
      audio.resume();
    }

    const agora = audio.currentTime;

    /*
     * Sirene digital curta:
     * dois tons sobrepostos e um pequeno estalo.
     */
    const tomA = audio.createOscillator();

    const tomB = audio.createOscillator();

    const ganhoA = audio.createGain();

    const ganhoB = audio.createGain();

    const base = this.contador <= 3 ? 760 : 430;

    tomA.type = 'square';

    tomB.type = 'sawtooth';

    tomA.frequency.setValueAtTime(base, agora);

    tomA.frequency.setValueAtTime(base * 1.35, agora + 0.08);

    tomB.frequency.setValueAtTime(base / 2, agora);

    tomB.frequency.exponentialRampToValueAtTime(Math.max(70, base / 5), agora + 0.24);

    ganhoA.gain.setValueAtTime(0.055, agora);

    ganhoA.gain.exponentialRampToValueAtTime(0.001, agora + 0.18);

    ganhoB.gain.setValueAtTime(0.025, agora);

    ganhoB.gain.exponentialRampToValueAtTime(0.001, agora + 0.26);

    tomA.connect(ganhoA);

    ganhoA.connect(audio.destination);

    tomB.connect(ganhoB);

    ganhoB.connect(audio.destination);

    tomA.start(agora);

    tomB.start(agora);

    tomA.stop(agora + 0.2);

    tomB.stop(agora + 0.28);
  }

  tocarImpactoFinal(): void {
    if (!this.audioContext) {
      return;
    }

    const audio = this.audioContext;

    if (audio.state === 'suspended') {
      audio.resume();
    }

    const agora = audio.currentTime;

    /*
     * Queda digital.
     */
    const queda = audio.createOscillator();

    const ganhoQueda = audio.createGain();

    queda.type = 'sawtooth';

    queda.frequency.setValueAtTime(920, agora);

    queda.frequency.exponentialRampToValueAtTime(38, agora + 0.85);

    ganhoQueda.gain.setValueAtTime(0.1, agora);

    ganhoQueda.gain.exponentialRampToValueAtTime(0.001, agora + 0.9);

    queda.connect(ganhoQueda);

    ganhoQueda.connect(audio.destination);

    /*
     * Ruído grave e fragmentado.
     */
    const duracao = 1.05;

    const buffer = audio.createBuffer(1, Math.floor(audio.sampleRate * duracao), audio.sampleRate);

    const dados = buffer.getChannelData(0);

    for (let i = 0; i < dados.length; i++) {
      const progresso = i / dados.length;

      const envelope = Math.pow(1 - progresso, 2);

      const fragmentacao = i % 13 < 4 ? 1 : 0.18;

      dados[i] = (Math.random() * 2 - 1) * envelope * fragmentacao;
    }

    const ruido = audio.createBufferSource();

    const filtro = audio.createBiquadFilter();

    const ganhoRuido = audio.createGain();

    ruido.buffer = buffer;

    filtro.type = 'lowpass';

    filtro.frequency.setValueAtTime(1800, agora);

    filtro.frequency.exponentialRampToValueAtTime(120, agora + 1);

    ganhoRuido.gain.setValueAtTime(0.08, agora);

    ganhoRuido.gain.exponentialRampToValueAtTime(0.001, agora + 1.03);

    ruido.connect(filtro);

    filtro.connect(ganhoRuido);

    ganhoRuido.connect(audio.destination);

    queda.start(agora);

    queda.stop(agora + 0.92);

    ruido.start(agora + 0.03);
  }

  novoJogo(): void {
    if (this.ehAdmin) {
      const chave = sessionStorage.getItem('adminChave');

      if (!chave) {
        return;
      }

      const headers = new HttpHeaders({
        'X-Admin-Key': chave,
      });

      this.http
        .post(
          `${this.apiUrl}/partidas`,
          {},
          {
            headers: headers,
          },
        )
        .subscribe({
          next: () => {
            this.router.navigate(['/painel']);
          },
        });

      return;
    }

    localStorage.removeItem('jogadorId');

    localStorage.removeItem('jogadorNome');

    localStorage.removeItem('partidaId');

    localStorage.removeItem('partidaIdResultado');

    this.router.navigate(['/']);
  }
}

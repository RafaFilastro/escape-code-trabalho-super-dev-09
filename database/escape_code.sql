-- ============================================================
-- ESCAPE CODE - Banco de dados inicial
-- ============================================================
-- Contém:
--   - estrutura das tabelas da aplicação;
--   - 100 desafios iniciais;
--   - nenhum jogador, partida ou tentativa de teste.
--
-- Compatível com MySQL 8.x.
-- ============================================================

CREATE DATABASE IF NOT EXISTS `escape_code`
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE `escape_code`;

SET FOREIGN_KEY_CHECKS = 0;

-- Remove as tabelas na ordem inversa das dependências.
DROP TABLE IF EXISTS `tentativas`;
DROP TABLE IF EXISTS `jogador_desafios`;
DROP TABLE IF EXISTS `jogadores`;
DROP TABLE IF EXISTS `partidas`;
DROP TABLE IF EXISTS `desafios`;

-- ============================================================
-- PARTIDAS
-- ============================================================

CREATE TABLE `partidas` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `codigo` VARCHAR(10) NOT NULL,
    `nome_protocolo` VARCHAR(80) NOT NULL,
    `status` VARCHAR(20) NOT NULL DEFAULT 'AGUARDANDO',
    `rodada_atual` INT NOT NULL DEFAULT 0,
    `duracao_segundos` INT NOT NULL DEFAULT 180,
    `duracao_rodada_segundos` INT NOT NULL DEFAULT 20,
    `chave_mestre` CHAR(10) NOT NULL,
    `motivo_fim` VARCHAR(40) DEFAULT NULL,
    `criado_em` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `iniciado_em` DATETIME(6) DEFAULT NULL,
    `rodada_iniciada_em` DATETIME(6) DEFAULT NULL,
    `finalizado_em` DATETIME(6) DEFAULT NULL,

    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_partidas_codigo` (`codigo`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- DESAFIOS
-- ============================================================

CREATE TABLE `desafios` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `tema` VARCHAR(30) NOT NULL,
    `pergunta` VARCHAR(500) NOT NULL,
    `alternativa_a` VARCHAR(255) NOT NULL,
    `alternativa_b` VARCHAR(255) NOT NULL,
    `alternativa_c` VARCHAR(255) NOT NULL,
    `alternativa_d` VARCHAR(255) NOT NULL,
    `alternativa_e` VARCHAR(255) NOT NULL,
    `resposta_correta` CHAR(1) NOT NULL,
    `fragmento_chave` CHAR(1) NOT NULL,
    `ativo` TINYINT(1) NOT NULL DEFAULT 1,

    PRIMARY KEY (`id`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- JOGADORES
-- ============================================================

CREATE TABLE `jogadores` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `partida_id` INT NOT NULL,
    `nome` VARCHAR(50) NOT NULL,
    `pontuacao` INT NOT NULL DEFAULT 0,
    `rodadas_concluidas` INT NOT NULL DEFAULT 0,
    `finalizado` TINYINT(1) NOT NULL DEFAULT 0,
    `finalizado_em` DATETIME(6) DEFAULT NULL,
    `criado_em` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_jogador_partida_nome` (`partida_id`, `nome`),

    CONSTRAINT `fk_jogadores_partida`
        FOREIGN KEY (`partida_id`)
        REFERENCES `partidas` (`id`)
        ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- DESAFIOS ATRIBUÍDOS A CADA JOGADOR
-- ============================================================

CREATE TABLE `jogador_desafios` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `jogador_id` INT NOT NULL,
    `desafio_id` INT NOT NULL,
    `rodada` INT NOT NULL,
    `criado_em` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_jogador_rodada` (`jogador_id`, `rodada`),
    UNIQUE KEY `uq_jogador_desafio` (`jogador_id`, `desafio_id`),

    CONSTRAINT `fk_jogador_desafios_jogador`
        FOREIGN KEY (`jogador_id`)
        REFERENCES `jogadores` (`id`)
        ON DELETE CASCADE,

    CONSTRAINT `fk_jogador_desafios_desafio`
        FOREIGN KEY (`desafio_id`)
        REFERENCES `desafios` (`id`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- TENTATIVAS
-- ============================================================

CREATE TABLE `tentativas` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `jogador_id` INT NOT NULL,
    `jogador_desafio_id` INT NOT NULL,
    `numero_tentativa` INT NOT NULL,
    `alternativa` CHAR(1) NOT NULL,
    `correta` TINYINT(1) NOT NULL,
    `pontos_ganhos` INT NOT NULL DEFAULT 0,
    `expirou` TINYINT(1) NOT NULL DEFAULT 0,
    `respondido_em` TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_tentativa_numero`
        (`jogador_id`, `jogador_desafio_id`, `numero_tentativa`),
    UNIQUE KEY `uq_tentativa_alternativa`
        (`jogador_id`, `jogador_desafio_id`, `alternativa`),

    CONSTRAINT `fk_tentativas_jogador`
        FOREIGN KEY (`jogador_id`)
        REFERENCES `jogadores` (`id`)
        ON DELETE CASCADE,

    CONSTRAINT `fk_tentativas_jogador_desafio`
        FOREIGN KEY (`jogador_desafio_id`)
        REFERENCES `jogador_desafios` (`id`)
        ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- CARGA INICIAL DE DESAFIOS
-- ============================================================
-- As alternativas são armazenadas em uma ordem base.
-- A aplicação é responsável por embaralhá-las para cada jogador.
-- ============================================================

-- HTML
INSERT INTO `desafios` (
    `id`,
    `tema`,
    `pergunta`,
    `alternativa_a`,
    `alternativa_b`,
    `alternativa_c`,
    `alternativa_d`,
    `alternativa_e`,
    `resposta_correta`,
    `fragmento_chave`,
    `ativo`
) VALUES
    (1,'HTML','Qual tag HTML é usada para criar um link?','<a>','<link>','<href>','<url>','<nav>','A','D',1),
    (2,'HTML','Qual tag HTML é usada para exibir uma imagem?','<img>','<image>','<picture-src>','<src>','<media>','A','L',1),
    (3,'HTML','Qual tag representa o título principal de uma página?','<h1>','<head>','<title>','<p>','<main-title>','A','T',1),
    (4,'HTML','Qual tag HTML é usada para criar um parágrafo?','<p>','<text>','<paragraph>','<span>','<article>','A','2',1),
    (5,'HTML','Qual tag cria uma lista não ordenada?','<ul>','<ol>','<li>','<list>','<dl>','A','9',1),
    (6,'HTML','Qual elemento é normalmente usado para criar um campo de entrada de dados?','<input>','<label>','<form>','<button>','<textarea-only>','A','G',1),
    (7,'HTML','Qual tag agrupa campos que serão enviados em um formulário?','<form>','<fieldset-only>','<input>','<send>','<data>','A','P',1),
    (8,'HTML','Qual tag é usada para inserir uma quebra de linha?','<br>','<hr>','<break>','<line>','<p>','A','W',1),
    (9,'HTML','Em qual tag fica o título mostrado na aba do navegador?','<title>','<h1>','<header>','<meta>','<caption>','A','5',1),
    (10,'HTML','Qual tag semântica é apropriada para uma área de navegação?','<nav>','<menuitem>','<navigate>','<header>','<aside>','A','C',1),
    (11,'HTML','Qual atributo identifica um elemento de forma única na página?','id','class','name','style','src','A','K',1),
    (12,'HTML','No elemento <a>, qual atributo informa o endereço de destino?','href','src','target','action','route','A','S',1),
    (13,'HTML','Para que serve principalmente o atributo alt de uma imagem?','Fornecer um texto alternativo','Alterar a largura da imagem','Criar um link','Aplicar uma classe CSS','Carregar a imagem mais rápido','A','Z',1),
    (14,'HTML','Qual atributo do <label> pode associá-lo ao id de um <input>?','for','href','src','target','value','A','8',1);

-- SCSS
INSERT INTO `desafios` (
    `id`,
    `tema`,
    `pergunta`,
    `alternativa_a`,
    `alternativa_b`,
    `alternativa_c`,
    `alternativa_d`,
    `alternativa_e`,
    `resposta_correta`,
    `fragmento_chave`,
    `ativo`
) VALUES
    (15,'SCSS','Qual propriedade CSS altera a cor do texto?','color','background','font-color','text-color','foreground','A','F',1),
    (16,'SCSS','Qual propriedade altera a cor de fundo de um elemento?','background-color','color','font-color','border-color-only','fill-text','A','N',1),
    (17,'SCSS','Qual propriedade define o espaço externo ao redor de um elemento?','margin','padding','gap-inside','border','spacing','A','V',1),
    (18,'SCSS','Qual propriedade define o espaço interno entre o conteúdo e a borda?','padding','margin','outline','gap','position','A','4',1),
    (19,'SCSS','Qual propriedade pode criar uma borda ao redor de um elemento?','border','outline-only','edge','frame','box-line','A','B',1),
    (20,'SCSS','Qual valor de display é muito usado para criar layouts flexíveis?','flex','block-only','absolute','inline-text','center','A','J',1),
    (21,'SCSS','Em um container flex, qual propriedade pode centralizar os itens horizontalmente no eixo principal?','justify-content','font-align','text-position','margin-content','place-text','A','R',1),
    (22,'SCSS','Qual propriedade altera o tamanho da fonte?','font-size','text-size','font-weight','size','line-size','A','Y',1),
    (23,'SCSS','Como selecionamos uma classe CSS chamada card?','.card','#card','card()','@card','*card','A','7',1),
    (24,'SCSS','Como selecionamos um elemento com id menu?','#menu','.menu','@menu','menu#','*menu','A','E',1),
    (25,'SCSS','Qual pseudo-classe é usada para estilizar um elemento quando o mouse passa sobre ele?',':hover',':click',':mouse',':focus-only',':over','A','M',1),
    (26,'SCSS','Em SCSS, qual símbolo normalmente inicia o nome de uma variável?','$','#','@','%','&','A','U',1),
    (27,'SCSS','Qual recurso do SCSS permite escrever seletores dentro de outros seletores?','Aninhamento','Compilação reversa','Herança de HTML','Roteamento','Tipagem','A','3',1),
    (28,'SCSS','Qual regra CSS é usada para aplicar estilos conforme o tamanho da tela?','@media','@screen','@responsive','@viewport-only','@device','A','A',1);

-- JAVASCRIPT
INSERT INTO `desafios` (
    `id`,
    `tema`,
    `pergunta`,
    `alternativa_a`,
    `alternativa_b`,
    `alternativa_c`,
    `alternativa_d`,
    `alternativa_e`,
    `resposta_correta`,
    `fragmento_chave`,
    `ativo`
) VALUES
    (29,'JAVASCRIPT','Qual palavra-chave cria uma variável cujo valor pode ser alterado?','let','const','fixed','var-only','change','A','H',1),
    (30,'JAVASCRIPT','Qual palavra-chave é usada para declarar uma constante?','const','let','static-only','fixed','final','A','Q',1),
    (31,'JAVASCRIPT','Qual comando exibe uma mensagem no console do navegador?','console.log()','print()','echo()','log.console()','write.console()','A','X',1),
    (32,'JAVASCRIPT','Qual estrutura é usada para executar código somente quando uma condição for verdadeira?','if','for','while','switch-only','function','A','6',1),
    (33,'JAVASCRIPT','Qual estrutura é normalmente usada para repetir um bloco de código várias vezes?','for','if','const','return','import','A','D',1),
    (34,'JAVASCRIPT','Qual palavra-chave é usada para declarar uma função tradicional?','function','def','func','method','procedure','A','L',1),
    (35,'JAVASCRIPT','Qual sintaxe representa um array vazio?','[]','{}','()','<>','||','A','T',1),
    (36,'JAVASCRIPT','Qual sintaxe representa um objeto vazio?','{}','[]','()','<>','##','A','2',1),
    (37,'JAVASCRIPT','Qual operador compara valor e tipo ao mesmo tempo?','===','==','=','!=','=>','A','9',1),
    (38,'JAVASCRIPT','Qual método adiciona um item ao final de um array?','push()','add()','append()','insert()','put()','A','G',1),
    (39,'JAVASCRIPT','Qual propriedade retorna a quantidade de itens de um array?','length','size','count','items','total','A','P',1),
    (40,'JAVASCRIPT','Qual função pode converter o texto \'10\' para um número inteiro?','parseInt()','toText()','string()','integerText()','parseString()','A','W',1),
    (41,'JAVASCRIPT','Qual método é usado para registrar um evento, como um clique, em um elemento?','addEventListener()','addClick()','onEventOnly()','listen()','event()','A','5',1),
    (42,'JAVASCRIPT','Qual sintaxe permite inserir uma variável dentro de um texto usando ${...}?','Template literal com crases','Aspas simples comuns','Comentário de bloco','Array literal','Objeto JSON','A','C',1);

-- TYPESCRIPT
INSERT INTO `desafios` (
    `id`,
    `tema`,
    `pergunta`,
    `alternativa_a`,
    `alternativa_b`,
    `alternativa_c`,
    `alternativa_d`,
    `alternativa_e`,
    `resposta_correta`,
    `fragmento_chave`,
    `ativo`
) VALUES
    (43,'TYPESCRIPT','Qual é uma das principais características adicionadas pelo TypeScript ao JavaScript?','Tipagem estática','Banco de dados embutido','Servidor web automático','CSS integrado','Substituição do HTML','A','K',1),
    (44,'TYPESCRIPT','Como declarar uma variável nome do tipo string?','let nome: string','string nome =','let string nome','nome -> string','var nome as text','A','S',1),
    (45,'TYPESCRIPT','Qual tipo representa números em TypeScript?','number','int-only','float-only','numeric','decimal-only','A','Z',1),
    (46,'TYPESCRIPT','Qual tipo representa valores verdadeiro ou falso?','boolean','bool-only','binary','bit-only','logic','A','8',1),
    (47,'TYPESCRIPT','Qual recurso é usado para descrever a estrutura de um objeto?','interface','database','template','route','module-only','A','F',1),
    (48,'TYPESCRIPT','Quando o TypeScript descobre automaticamente o tipo pelo valor atribuído, isso é chamado de quê?','Inferência de tipo','Herança','Compilação reversa','Polimorfismo','Roteamento','A','N',1),
    (49,'TYPESCRIPT','Antes de rodar no navegador, o TypeScript é normalmente convertido para qual linguagem?','JavaScript','Python','Java','C#','SQL','A','V',1),
    (50,'TYPESCRIPT','Em uma interface, qual símbolo torna uma propriedade opcional?','?','!','#','$','%','A','4',1),
    (51,'TYPESCRIPT','Qual palavra-chave pode impedir a reatribuição de uma propriedade de objeto em TypeScript?','readonly','constant','final','locked','static-only','A','B',1),
    (52,'TYPESCRIPT','Qual operador permite definir que um valor pode ter mais de um tipo, como string | number?','|','&','||','+',':','A','J',1),
    (53,'TYPESCRIPT','Qual tipo desativa grande parte da verificação de tipos para um valor?','any','all','object-only','unknown-only','dynamic','A','R',1),
    (54,'TYPESCRIPT','Qual opção representa corretamente um array de números?','number[]','number{}','array<number-only>','numbers()','int-list','A','Y',1),
    (55,'TYPESCRIPT','Como indicar que uma função retorna uma string?','(): string','=> returns string','function:string()','(): text-only','returns(string)','A','7',1),
    (56,'TYPESCRIPT','Qual recurso agrupa um conjunto de valores nomeados, como ADMIN e USUARIO?','enum','loop','tuple-only','router','decorator-only','A','E',1);

-- ANGULAR
INSERT INTO `desafios` (
    `id`,
    `tema`,
    `pergunta`,
    `alternativa_a`,
    `alternativa_b`,
    `alternativa_c`,
    `alternativa_d`,
    `alternativa_e`,
    `resposta_correta`,
    `fragmento_chave`,
    `ativo`
) VALUES
    (57,'ANGULAR','Qual comando cria um novo projeto Angular?','ng new','ng create','angular start','npm angular','ng project','A','M',1),
    (58,'ANGULAR','Qual comando inicia normalmente o servidor de desenvolvimento Angular?','ng serve','ng run-server','angular dev','npm start-angular','ng host','A','U',1),
    (59,'ANGULAR','Qual elemento básico do Angular controla uma parte da interface?','Componente','Tabela SQL','Thread','Container Docker','Classe CSS apenas','A','3',1),
    (60,'ANGULAR','Qual arquivo de um componente normalmente contém a estrutura visual da página?','Arquivo HTML do template','Arquivo SQL','Arquivo .env','package-lock apenas','Arquivo Python','A','A',1),
    (61,'ANGULAR','Qual arquivo de um componente normalmente contém seus estilos?','Arquivo .scss ou .css','Arquivo .sql','Arquivo .py','Arquivo .json apenas','Arquivo .md','A','H',1),
    (62,'ANGULAR','Qual sintaxe mostra o valor de uma variável no template Angular?','{{ valor }}','${valor}','<valor>','[valor]','(valor)','A','Q',1),
    (63,'ANGULAR','Qual sintaxe liga um clique de botão a uma função?','(click)=\"funcao()\"','[click]=\"funcao()\"','{{ click }}','click=>funcao','@click(funcao)','A','X',1),
    (64,'ANGULAR','Qual sintaxe é usada para property binding?','[propriedade]=\"valor\"','(propriedade)=\"valor\"','{{ propriedade=valor }}','@propriedade','#propriedade','A','6',1),
    (65,'ANGULAR','Qual sintaxe é conhecida como two-way binding com ngModel?','[(ngModel)]','[ngModel]','(ngModel)','{{ngModel}}','@ngModel','A','D',1),
    (66,'ANGULAR','Qual bloco atual do template Angular pode exibir conteúdo de forma condicional?','@if','@when-only','#if','*condition','if()','A','L',1),
    (67,'ANGULAR','Qual bloco atual do template Angular pode repetir elementos de uma lista?','@for','@repeat-only','#loop','*each','foreach()','A','T',1),
    (68,'ANGULAR','Qual recurso do Angular é usado para fazer requisições HTTP para uma API?','HttpClient','Router','FormsModule','Component','StyleUrl','A','2',1),
    (69,'ANGULAR','Qual elemento marca o local onde o Angular renderiza o componente da rota ativa?','<router-outlet>','<route-view>','<ng-page>','<app-router>','<router-page>','A','9',1),
    (70,'ANGULAR','Para que serve o arquivo de rotas da aplicação?','Associar URLs a componentes','Criar tabelas do banco','Compilar SCSS manualmente','Instalar o Node.js','Armazenar senhas','A','G',1),
    (71,'ANGULAR','Qual método de ciclo de vida é executado quando o componente é inicializado?','ngOnInit()','ngStart()','onLoadAngular()','initComponent()','ngCreate()','A','P',1),
    (72,'ANGULAR','Qual conceito do Angular permite fornecer uma dependência a uma classe pelo construtor?','Injeção de dependência','Herança de CSS','Normalização SQL','Serialização HTML','Compilação binária','A','W',1);

-- PYTHON
INSERT INTO `desafios` (
    `id`,
    `tema`,
    `pergunta`,
    `alternativa_a`,
    `alternativa_b`,
    `alternativa_c`,
    `alternativa_d`,
    `alternativa_e`,
    `resposta_correta`,
    `fragmento_chave`,
    `ativo`
) VALUES
    (73,'PYTHON','Qual função exibe uma mensagem na tela em Python?','print()','console.log()','echo()','write()','show()','A','5',1),
    (74,'PYTHON','Qual palavra-chave é usada para criar uma função?','def','function','func','method','create','A','C',1),
    (75,'PYTHON','Qual estrutura é usada para executar um bloco quando uma condição é verdadeira?','if','for','def','import','class-only','A','K',1),
    (76,'PYTHON','Qual estrutura pode percorrer os itens de uma lista?','for','if','print','return','try-only','A','S',1),
    (77,'PYTHON','Qual sintaxe representa uma lista vazia?','[]','{}','()','<>','||','A','Z',1),
    (78,'PYTHON','Qual sintaxe representa um dicionário vazio?','{}','[]','()','<>','##','A','8',1),
    (79,'PYTHON','Qual função retorna a quantidade de itens de uma lista?','len()','countAll()','size()','length()','total()','A','F',1),
    (80,'PYTHON','Qual função lê um valor digitado pelo usuário no terminal?','input()','read()','scan()','prompt()','keyboard()','A','N',1),
    (81,'PYTHON','Qual função converte o texto \'10\' para número inteiro?','int()','number()','parseInt()','integerText()','toNumber()','A','V',1),
    (82,'PYTHON','Qual método adiciona um item ao final de uma lista?','append()','push()','add()','insertEnd()','put()','A','4',1),
    (83,'PYTHON','O que range(3) gera para uso comum em um for?','0, 1 e 2','1, 2 e 3','0, 1, 2 e 3','Somente 3','Uma string \'3\'','A','B',1),
    (84,'PYTHON','Qual palavra-chave importa uma biblioteca ou módulo?','import','include','using','require','load','A','J',1),
    (85,'PYTHON','Qual símbolo inicia um comentário de uma linha em Python?','#','//','/*','--','<!--','A','R',1),
    (86,'PYTHON','Qual estrutura é usada para tratar exceções em Python?','try / except','if / else','for / while','switch / case','begin / rescue-only','A','Y',1);

-- MYSQL
INSERT INTO `desafios` (
    `id`,
    `tema`,
    `pergunta`,
    `alternativa_a`,
    `alternativa_b`,
    `alternativa_c`,
    `alternativa_d`,
    `alternativa_e`,
    `resposta_correta`,
    `fragmento_chave`,
    `ativo`
) VALUES
    (87,'MYSQL','Qual comando SQL é usado para consultar registros?','SELECT','INSERT','UPDATE','DELETE','CREATE','A','7',1),
    (88,'MYSQL','Qual comando adiciona novos registros a uma tabela?','INSERT','SELECT','UPDATE','DELETE','ALTER','A','E',1),
    (89,'MYSQL','Qual comando modifica registros existentes?','UPDATE','SELECT','INSERT','CREATE','SHOW','A','M',1),
    (90,'MYSQL','Qual comando remove registros de uma tabela?','DELETE','DROP COLUMN','SELECT','INSERT','UPDATE','A','U',1),
    (91,'MYSQL','Qual comando cria uma nova tabela?','CREATE TABLE','NEW TABLE','ADD TABLE','MAKE TABLE','INSERT TABLE','A','3',1),
    (92,'MYSQL','Qual cláusula filtra registros de acordo com uma condição?','WHERE','ORDER BY','GROUP BY','FROM','VALUES','A','A',1),
    (93,'MYSQL','Qual cláusula pode ordenar o resultado de uma consulta?','ORDER BY','SORT','WHERE','GROUP ONLY','ARRANGE','A','H',1),
    (94,'MYSQL','Qual recurso combina dados relacionados de duas ou mais tabelas?','JOIN','MERGE TEXT','APPEND','UNION ONLY','CONNECT ROW','A','Q',1),
    (95,'MYSQL','Qual chave identifica de forma única cada registro de uma tabela?','PRIMARY KEY','FOREIGN KEY','INDEX ONLY','DEFAULT','NOT NULL','A','X',1),
    (96,'MYSQL','Qual chave cria uma relação com outra tabela?','FOREIGN KEY','PRIMARY KEY','AUTO_INCREMENT','DEFAULT','UNIQUE ONLY','A','6',1),
    (97,'MYSQL','Qual função conta quantos registros foram retornados?','COUNT()','SUM()','TOTAL()','LENGTH()','ROWS()','A','D',1),
    (98,'MYSQL','Qual opção faz um campo numérico incrementar automaticamente a cada novo registro?','AUTO_INCREMENT','AUTO_NUMBER','NEXT_ID','INCREMENT','SERIAL_ONLY','A','L',1),
    (99,'MYSQL','Qual restrição impede que uma coluna receba valor NULL?','NOT NULL','NO EMPTY','REQUIRED','UNIQUE','DEFAULT','A','T',1),
    (100,'MYSQL','Qual cláusula agrupa registros que possuem valores em comum?','GROUP BY','ORDER BY','WHERE','HAVING ONLY','COLLECT BY','A','2',1);

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================
-- Fim da instalação inicial do Escape Code.
-- ============================================================

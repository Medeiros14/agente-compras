import { IconeCheck, IconeX } from "./Icones";
import type { FerramentaChamada } from "./tipos";

/** Trilha recolhida das ferramentas do MCP que o agente chamou, na ordem. */
export function FerramentasChamadas({ chamadas }: { chamadas: FerramentaChamada[] }) {
  if (chamadas.length === 0) return null;
  const rotulo = chamadas.length === 1 ? "1 ferramenta chamada" : `${chamadas.length} ferramentas chamadas`;

  return (
    <details className="trilha">
      <summary>{rotulo}</summary>
      <ol>
        {chamadas.map((chamada, i) => (
          <li key={i} className={chamada.ok ? "trilha-ok" : "trilha-falha"}>
            <span className="trilha-marca">
              {chamada.ok ? <IconeCheck className="icone-14" /> : <IconeX className="icone-14" />}
            </span>
            <div>
              <code className="trilha-nome">{chamada.nome}</code>
              {chamada.erro && <span className="trilha-erro">{chamada.erro}</span>}
              <pre>{JSON.stringify(chamada.argumentos, null, 2)}</pre>
            </div>
          </li>
        ))}
      </ol>
    </details>
  );
}

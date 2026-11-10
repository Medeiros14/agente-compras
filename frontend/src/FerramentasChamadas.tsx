import type { FerramentaChamada } from "./tipos";

/** Mostra, recolhido, quais ferramentas do MCP o agente chamou e com quais argumentos. */
export function FerramentasChamadas({ chamadas }: { chamadas: FerramentaChamada[] }) {
  if (chamadas.length === 0) return null;

  return (
    <details className="ferramentas">
      <summary>Ferramentas chamadas ({chamadas.length})</summary>
      <ol>
        {chamadas.map((chamada, i) => (
          <li key={i}>
            <span className={chamada.ok ? "status-ok" : "status-erro"}>{chamada.ok ? "✓" : "✗"}</span>{" "}
            <code>{chamada.nome}</code>
            {chamada.erro && <span className="status-erro"> {chamada.erro}</span>}
            <pre>{JSON.stringify(chamada.argumentos, null, 2)}</pre>
          </li>
        ))}
      </ol>
    </details>
  );
}

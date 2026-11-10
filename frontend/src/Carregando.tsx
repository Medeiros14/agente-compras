import { useEffect, useState } from "react";

/** Mostrado enquanto o agente trabalha (5 a 15s): mensagem, barra indeterminada e tempo decorrido. */
export function Carregando() {
  const [segundos, setSegundos] = useState(0);

  useEffect(() => {
    const inicio = Date.now();
    const timer = setInterval(() => setSegundos(Math.floor((Date.now() - inicio) / 1000)), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="carregando" role="status" aria-live="polite">
      <div className="carregando-linha">
        <span>Buscando no catálogo e conferindo preços…</span>
        <span className="carregando-tempo">{segundos}s</span>
      </div>
      <div className="carregando-barra" aria-hidden="true">
        <span />
      </div>
      {segundos >= 12 && <p className="carregando-dica">Pedidos com várias buscas podem levar até meio minuto.</p>}
    </div>
  );
}

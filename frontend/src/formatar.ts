const moeda = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "USD" });
const dataHora = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" });

export const formatarDolar = (valor: number) => moeda.format(valor);
export const formatarData = (iso: string) => dataHora.format(new Date(iso));

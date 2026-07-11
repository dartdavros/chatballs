/**
 * @startingPoint section="Cards" subtitle="Single integration row (connected/degraded/error)" viewport="700x90"
 */
export interface IntegrationHealthCardProps {
  name: string;
  group: string;
  status?: "connected" | "degraded" | "error";
}

export function IntegrationHealthCard(props: IntegrationHealthCardProps): JSX.Element;

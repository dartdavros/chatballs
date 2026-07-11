export interface AvatarProps {
  /** 1-2 letter initials, e.g. "ИП". */
  initials: string;
  /** Background color — the baseline assigns a distinct color per person (see palette in Colors cards). */
  color?: string;
  size?: number;
}

export function Avatar(props: AvatarProps): JSX.Element;

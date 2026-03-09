export default function ForecastInput({ value, onChange }) {
  return (
    <select value={value} onChange={(e) => onChange(Number(e.target.value))}>
      <option value={7}>7 days</option>
      <option value={15}>15 days</option>
      <option value={30}>30 days</option>
      <option value={60}>60 days</option>
    </select>
  );
}

"use client";

interface Filters {
  min_price?: string;
  max_price?: string;
  min_volume?: string;
  signal?: string;
}

interface Props {
  filters: Filters;
  onChange: (filters: Filters) => void;
}

export default function FilterPanel({ filters, onChange }: Props) {
  const update = (key: string, value: string) => {
    onChange({ ...filters, [key]: value });
  };

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="text-oracle-muted text-xs">Min Price</label>
          <input
            type="number"
            value={filters.min_price || ""}
            onChange={(e) => update("min_price", e.target.value)}
            placeholder="0"
            className="w-full mt-1 bg-oracle-bg border border-oracle-border rounded px-2 py-1.5 text-sm text-oracle-text"
          />
        </div>
        <div>
          <label className="text-oracle-muted text-xs">Max Price</label>
          <input
            type="number"
            value={filters.max_price || ""}
            onChange={(e) => update("max_price", e.target.value)}
            placeholder="∞"
            className="w-full mt-1 bg-oracle-bg border border-oracle-border rounded px-2 py-1.5 text-sm text-oracle-text"
          />
        </div>
      </div>

      <div>
        <label className="text-oracle-muted text-xs">Min Volume</label>
        <input
          type="number"
          value={filters.min_volume || ""}
          onChange={(e) => update("min_volume", e.target.value)}
          placeholder="0"
          className="w-full mt-1 bg-oracle-bg border border-oracle-border rounded px-2 py-1.5 text-sm text-oracle-text"
        />
      </div>

      <div>
        <label className="text-oracle-muted text-xs">Signal</label>
        <select
          value={filters.signal || ""}
          onChange={(e) => update("signal", e.target.value)}
          className="w-full mt-1 bg-oracle-bg border border-oracle-border rounded px-2 py-1.5 text-sm text-oracle-text"
        >
          <option value="">All</option>
          <option value="strong_buy">Strong Buy</option>
          <option value="buy">Buy</option>
          <option value="neutral">Neutral</option>
          <option value="sell">Sell</option>
          <option value="strong_sell">Strong Sell</option>
        </select>
      </div>
    </div>
  );
}

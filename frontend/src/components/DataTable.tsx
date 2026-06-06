import type { RunArtifact, TableColumn } from "../types";

function formatCellValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "-";
  return String(value);
}

export function DataTable<TData extends object>({
  rows,
  columns,
  getRowId
}: {
  rows: TData[];
  columns: Array<TableColumn<TData>>;
  getRowId?: (row: TData, rowIndex: number) => string;
}) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={String(column.key)} style={{ width: column.width, textAlign: column.align ?? "left" }}>
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={getRowId?.(row, rowIndex) ?? rowIndex}>
              {columns.map((column) => (
                <td key={String(column.key)} style={{ textAlign: column.align ?? "left" }}>
                  {column.render ? column.render(row, rowIndex) : formatCellValue(row[column.key as keyof TData])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ArtifactTable({ artifact }: { artifact: RunArtifact }) {
  const columns = artifact.preview?.columns ?? [];
  const rows = artifact.preview?.rows ?? [];

  if (!columns.length || !rows.length) {
    return <div className="table-empty">No preview</div>;
  }

  return (
    <DataTable<Record<string, unknown>>
      rows={rows.slice(0, 5)}
      columns={columns.map((column) => ({ key: column, header: column }))}
    />
  );
}

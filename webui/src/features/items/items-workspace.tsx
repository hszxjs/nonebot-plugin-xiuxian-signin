import { Card, List, Pagination, Select, Space, Tag, Typography } from "antd"
import { useMemo, useState } from "react"
import {
  EmptyPanel,
  PageHeader,
  SearchField,
  TagList,
} from "@/features/shared/ui"
import { assetUrl } from "@/lib/api"
import type { ItemEntry, ItemsPayload } from "@/lib/types"

function encodeAssetPath(path: string) {
  return path
    .split("/")
    .map((part) => encodeURIComponent(part))
    .join("/")
}

function itemMatches(item: ItemEntry, query: string, category: string) {
  const text = [item.name, item.category, item.source, item.usage, item.story]
    .join("\n")
    .toLowerCase()
  const matchesQuery =
    !query.trim() || text.includes(query.trim().toLowerCase())
  const matchesCategory = category === "all" || item.category === category
  return matchesQuery && matchesCategory
}

export function ItemsWorkspace({ payload }: { payload: ItemsPayload }) {
  const [query, setQuery] = useState("")
  const [category, setCategory] = useState("all")
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(48)
  const filteredItems = useMemo(
    () => payload.items.filter((item) => itemMatches(item, query, category)),
    [category, payload.items, query],
  )
  const pagedItems = useMemo(() => {
    const start = (currentPage - 1) * pageSize
    return filteredItems.slice(start, start + pageSize)
  }, [currentPage, filteredItems, pageSize])

  return (
    <div className="workspace-stack">
      <PageHeader
        title="物品图鉴"
        description="展示签到、秘境、商店等玩法中可出现的物品，支持按领域含义筛选。"
      />

      <Card title="筛选">
        <div className="two-column">
          <SearchField
            value={query}
            onChange={(value) => {
              setQuery(value)
              setCurrentPage(1)
            }}
            placeholder="搜索物品或来源"
          />
          <Select
            value={category}
            onChange={(value) => {
              setCategory(value)
              setCurrentPage(1)
            }}
            options={[
              { value: "all", label: "全部类别" },
              ...payload.meta.categories.map((name) => ({
                value: name,
                label: name,
              })),
            ]}
          />
        </div>
      </Card>

      <Card
        title="物品条目"
        extra={`${filteredItems.length} / ${payload.items.length} 个条目`}
      >
        {filteredItems.length ? (
          <List
            dataSource={pagedItems}
            renderItem={(item) => (
              <List.Item
                actions={[
                  item.required_realm ? (
                    <Tag key="realm">{item.required_realm}</Tag>
                  ) : null,
                  item.source ? <Tag key="source">{item.source}</Tag> : null,
                ].filter(Boolean)}
              >
                <List.Item.Meta
                  avatar={
                    item.icon ? (
                      <img
                        className="item-thumb"
                        loading="lazy"
                        decoding="async"
                        src={assetUrl(
                          `/assets/item-icons/${encodeAssetPath(item.icon)}`,
                        )}
                        alt={item.name}
                      />
                    ) : undefined
                  }
                  title={
                    <Space wrap>
                      <span>{item.name}</span>
                      {item.category ? <Tag>{item.category}</Tag> : null}
                      {item.customized ? (
                        <Tag color="processing">已覆盖</Tag>
                      ) : null}
                    </Space>
                  }
                  description={
                    <Space orientation="vertical">
                      <Typography.Text type="secondary">
                        {item.usage || item.story || item.source || "暂无描述"}
                      </Typography.Text>
                      <Space wrap>
                        <TagList values={item.tiers} />
                        <TagList values={item.grades} />
                      </Space>
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        ) : (
          <EmptyPanel
            title="没有匹配物品"
            description="调整搜索词或类别后再查看。"
          />
        )}
        {filteredItems.length > pageSize ? (
          <Pagination
            current={currentPage}
            pageSize={pageSize}
            total={filteredItems.length}
            showSizeChanger
            pageSizeOptions={[24, 48, 96, 160]}
            onChange={(page, size) => {
              setCurrentPage(page)
              setPageSize(size)
            }}
          />
        ) : null}
      </Card>
    </div>
  )
}

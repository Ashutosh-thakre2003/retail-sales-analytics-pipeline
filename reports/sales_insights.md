# Retail Sales Insights Report

Generated 2026-10-23 from the `reporting` schema in PostgreSQL. Source: Sample Superstore, orders from 2014-01-03 to 2017-12-30.

## Headline numbers

| Sales | Profit | Margin | Orders | Customers | Products | Units | Discount given |
| --- | --- | --- | --- | --- | --- | --- | --- |
| $2,297,201 | $286,397 | 12.5% | 5,009 | 793 | 1,862 | 37,873 | $566,734 |

## Key findings

1. **Growth:** sales grew from $484,248 in 2014 to $733,215 in 2017 (14.8% a year on average), and profit grew 88.6% over the same period.
2. **Profitability:** the overall profit margin is 12.5%. 18.7% of sales lines lose money, costing $156,131 in total.
3. **Discounts:** lines with no discount earn a 29.5% margin, while discounts of 41%+ produce a -77.4% margin, with 100.0% of those lines losing money.
4. **Loss-making sub-categories:** Tables (-$17,725, avg discount 26.1%), Bookcases (-$3,473, avg discount 21.1%), Supplies (-$1,189, avg discount 7.7%).
5. **Regions:** West has the best margin (14.9%) and Central the weakest (7.9%). The biggest losses by state are Texas (-$25,729, avg discount 37.0%), Ohio (-$16,971, avg discount 32.5%), Pennsylvania (-$15,560, avg discount 32.9%), Illinois (-$12,608, avg discount 39.0%), North Carolina (-$7,491, avg discount 28.3%), compared with a company-wide average discount of 15.6%.
6. **Seasonality:** 38.2% of all sales fall in October to December, and November is the strongest month.
7. **Customers:** the top 25% of customers generate 55.1% of sales, and 98.5% of customers ordered more than once.
8. **Products:** 304 of 1,894 products lost money over the whole period (a product is an ID and name pair; 1,862 distinct IDs).
9. **Shipping:** average time from order to shipment is 4.0 days, ranging from 0.0 (Same Day) to 5.0 (Standard Class).

## Recommendations

- Cap discounts at 20% unless a promotion is shown to be profitable: every band above 20% has a negative margin.
- Review pricing, supplier costs and discount policy for the loss-making sub-categories listed above.
- Review discounting in the worst states by profit, where average discounts are well above the company average.
- Plan inventory and marketing around the Q4 peak.
- Protect the top customer quartile with retention offers, since it drives most of the revenue.

## Yearly performance

| Year | Sales | Profit | Margin | Orders | Avg order value | Sales YoY |
| --- | --- | --- | --- | --- | --- | --- |
| 2014 | $484,248 | $49,544 | 10.2% | 969 | $499.74 | n/a |
| 2015 | $470,533 | $61,619 | 13.1% | 1,038 | $453.31 | -2.8% |
| 2016 | $609,206 | $81,795 | 13.4% | 1,315 | $463.27 | 29.5% |
| 2017 | $733,215 | $93,439 | 12.7% | 1,687 | $434.63 | 20.4% |

## Region performance

| Region | Sales | Profit | Margin | Avg discount |
| --- | --- | --- | --- | --- |
| West | $725,458 | $108,418 | 14.9% | 10.9% |
| East | $678,781 | $91,523 | 13.5% | 14.5% |
| Central | $501,240 | $39,706 | 7.9% | 24.0% |
| South | $391,722 | $46,749 | 11.9% | 14.7% |

## Segment performance

| Segment | Customers | Sales | Profit | Margin |
| --- | --- | --- | --- | --- |
| Consumer | 409 | $1,161,401 | $134,119 | 11.6% |
| Corporate | 236 | $706,146 | $91,979 | 13.0% |
| Home Office | 148 | $429,653 | $60,299 | 14.0% |

## Discount impact

| Discount band | Lines | Sales | Profit | Margin | Loss-making lines |
| --- | --- | --- | --- | --- | --- |
| No discount | 4,798 | $1,087,908 | $320,988 | 29.5% | 0.0% |
| 1-20% | 3,803 | $846,522 | $100,785 | 11.9% | 13.8% |
| 21-40% | 460 | $234,138 | -$35,817 | -15.3% | 90.2% |
| 41%+ | 933 | $128,632 | -$99,559 | -77.4% | 100.0% |

## Sub-category profitability (worst first)

| Category | Sub-category | Sales | Profit | Margin | Avg discount |
| --- | --- | --- | --- | --- | --- |
| Furniture | Tables | $206,966 | -$17,725 | -8.6% | 26.1% |
| Furniture | Bookcases | $114,880 | -$3,473 | -3.0% | 21.1% |
| Office Supplies | Supplies | $46,674 | -$1,189 | -2.5% | 7.7% |
| Office Supplies | Fasteners | $3,024 | $950 | 31.4% | 8.2% |
| Technology | Machines | $189,239 | $3,385 | 1.8% | 30.6% |
| Office Supplies | Labels | $12,486 | $5,546 | 44.4% | 6.9% |
| Office Supplies | Art | $27,119 | $6,528 | 24.1% | 7.5% |
| Office Supplies | Envelopes | $16,476 | $6,964 | 42.3% | 8.0% |
| Furniture | Furnishings | $91,705 | $13,059 | 14.2% | 13.8% |
| Office Supplies | Appliances | $107,532 | $18,138 | 16.9% | 16.7% |
| Office Supplies | Storage | $223,844 | $21,279 | 9.5% | 7.5% |
| Furniture | Chairs | $328,449 | $26,590 | 8.1% | 17.0% |
| Office Supplies | Binders | $203,413 | $30,222 | 14.9% | 37.2% |
| Office Supplies | Paper | $78,479 | $34,054 | 43.4% | 7.5% |
| Technology | Accessories | $167,380 | $41,937 | 25.1% | 7.8% |
| Technology | Phones | $330,007 | $44,516 | 13.5% | 15.5% |
| Technology | Copiers | $149,528 | $55,618 | 37.2% | 16.2% |

## Shipping

| Ship mode | Orders | Avg days to ship | Sales | Margin |
| --- | --- | --- | --- | --- |
| Same Day | 264 | 0.0 | $128,363 | 12.4% |
| First Class | 787 | 2.2 | $351,428 | 13.9% |
| Second Class | 964 | 3.2 | $459,194 | 12.5% |
| Standard Class | 2,994 | 5.0 | $1,358,216 | 12.1% |

## Top 10 customers by sales

| Customer | Segment | Orders | Sales | Profit |
| --- | --- | --- | --- | --- |
| Sean Miller | Home Office | 5 | $25,043 | -$1,981 |
| Tamara Chand | Corporate | 5 | $19,052 | $8,981 |
| Raymond Buch | Consumer | 6 | $15,117 | $6,976 |
| Tom Ashbrook | Home Office | 4 | $14,596 | $4,704 |
| Adrian Barton | Consumer | 10 | $14,474 | $5,445 |
| Ken Lonsdale | Consumer | 12 | $14,175 | $807 |
| Sanjit Chand | Consumer | 9 | $14,142 | $5,757 |
| Hunter Lopez | Consumer | 6 | $12,873 | $5,622 |
| Sanjit Engle | Consumer | 11 | $12,209 | $2,651 |
| Christopher Conant | Consumer | 5 | $12,129 | $2,177 |

CSV extracts of every summary view are in `reports/extracts/`.

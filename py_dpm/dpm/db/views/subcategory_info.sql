CREATE OR ALTER VIEW subcategory_item_info AS
SELECT ic.Code  as item_code,
       ic.IsDefaultItem as is_default_item,
       scv.SubCategoryID as subcategory_id,
       icp.Code as parent_item_code,
       sci."Order" as ordering,
       oa.Name as arithmetic_operator,
       oc.Symbol as comparison_symbol,
       scv.StartReleaseID as start_release_id,
       scv.EndReleaseID as end_release_id
from SubCategoryItem sci
         inner join SubCategoryVersion scv
                    on scv.SubCategoryVID = sci.SubCategoryVID
         inner join ItemCategory ic on sci.ItemID = ic.ItemID
         left join ItemCategory icp on sci.ParentItemID = icp.ItemID
         left join Operator oa on sci.ArithmeticOperatorID = oa.OperatorID
         left join Operator oc on sci.ComparisonOperatorID = oc.OperatorID

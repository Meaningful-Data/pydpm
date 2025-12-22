CREATE
OR ALTER
VIEW operation_info AS
select opN.NodeID as operation_node_id,
       opN.OperationVID as operation_version_id,
       opN.ParentNodeID as parent_node_id,
       O.OperatorID as operator_id,
       O.Symbol as symbol,
       opA.Name as argument,
       opA.[Order] as operator_argument_order,
       opN.IsLeaf as is_leaf,
       opN.Scalar as scalar,
       opR.OperandReferenceId as operand_reference_id,
       opR.OperandReference as operand_reference,
       opR.ItemID as item_id,
       opR.PropertyID as property_id,
       opR.VariableID as variable_id,
       opR.x,
       opR.y,
       opR.z,
       opN.UseIntervalArithmetics as use_interval_arithmetics,
       opN.FallbackValue as fallback_value
from [dbo].OperationNode opN
         left join [dbo].OperandReference opR on opN.NodeID = opR.NodeID
         left join [dbo].Operator O on O.OperatorID = opN.OperatorID
         left join [dbo].OperatorArgument opA
                   on opN.ArgumentID = opA.ArgumentID;
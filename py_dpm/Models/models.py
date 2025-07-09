from datetime import datetime
from typing import List

import pandas as pd
from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, NVARCHAR, String, and_, or_, \
    select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import aliased, declarative_base, relationship

from py_dpm.Utils.tokens import EXISTENCE, FILING_INDICATOR, HIERARCHY, SIGN, TABLE_VERSION_ID

Base = declarative_base()

"""
Models for tables included in the Operation Model from DPM Refit.
"""


class OperationScope(Base):
    __tablename__ = 'OperationScope'

    OperationScopeID = Column(Integer, primary_key=True)
    OperationVID = Column(Integer, ForeignKey('OperationVersion.OperationVID'), nullable=False)
    IsActive = Column(Boolean, nullable=False)
    Severity = Column(NVARCHAR(20), nullable=False)
    FromSubmissionDate = Column(Date, nullable=False)
    RowGUID = Column(UUID(as_uuid=True), nullable=False)

    operation_version = relationship('OperationVersion', back_populates='operation_scopes')
    composition = relationship('OperationScopeComposition', back_populates='operation_scope')


class OperationScopeComposition(Base):
    __tablename__ = 'OperationScopeComposition'

    OperationScopeID = Column(Integer, ForeignKey('OperationScope.OperationScopeID'), primary_key=True)
    ModuleVID = Column(Integer, ForeignKey('ModuleVersion.ModuleVID'), primary_key=True)
    RowGUID = Column(UUID(as_uuid=True), nullable=False)

    operation_scope = relationship('OperationScope', back_populates='composition')
    module_version = relationship('ModuleVersion', back_populates='operation_scope_compositions')

    @classmethod
    def get_from_operation_version_id(cls, session, operation_version_id):
        query = session.query(cls).join(OperationScope, and_(OperationScope.OperationScopeID == cls.OperationScopeID,
                                                             OperationScope.OperationVID == operation_version_id))
        return pd.read_sql_query(query.statement, session.connection(close_with_result=True))

    @classmethod
    def is_duplicated(cls, session):
        query = session.query(cls.OperationScopeID, cls.ModuleVID)
        df = pd.read_sql_query(query.statement, session.connection(close_with_result=True))
        duplicateRows = df[df.duplicated()]
        if len(duplicateRows) > 0:
            return True, duplicateRows
        return False, None


class OperationNode(Base):
    __tablename__ = "OperationNode"

    NodeID = Column(
        Integer,
        primary_key=True
    )

    OperationVID = Column(
        Integer,
        # ForeignKey('OperationVersion.OperationVID')
    )
    # IDs
    ParentNodeID = Column(Integer, ForeignKey('OperationNode.NodeID'), nullable=True)
    OperatorID = Column(Integer, nullable=True)
    ArgumentID = Column(Integer, nullable=True)
    # Tolerances
    AbsoluteTolerance = Column(String, nullable=True)
    RelativeTolerance = Column(String, nullable=True)

    # Operand extra info
    FallbackValue = Column(String, nullable=True)
    UseIntervalArithmetics = Column(Boolean)
    OperandType = Column(String)
    IsLeaf = Column(Boolean)
    Scalar = Column(String, nullable=True)

    # Relationships
    parent = relationship('OperationNode', remote_side=[NodeID], back_populates='children')
    children = relationship('OperationNode', back_populates='parent')
    operand_reference = relationship('OperandReference', back_populates="op_node")

    @classmethod
    def get_ml(cls, session, operation_vid):
        """
        """
        query = session.query(cls).filter(cls.OperationVID == operation_vid)
        df=pd.read_sql_query(query.statement, session.connection(close_with_result=True))
        if df.empty:
            return None
        parent = df[pd.isnull(df['ParentNodeID'])]
        operation_node = OperationNode(
            OperatorID=parent['OperatorID'].iloc[0],
            OperationVID=parent['OperationVID'].iloc[0],
            parent=None,
            Scalar=parent['Scalar'].iloc[0],
            UseIntervalArithmetics=parent['UseIntervalArithmetics'].iloc[0],
            FallbackValue=parent['FallbackValue'].iloc[0],
            IsLeaf=parent['IsLeaf'].iloc[0],
            ArgumentID=parent['ArgumentID'].iloc[0],
            NodeID=parent['NodeID'].iloc[0]
        )

        aux_list = [operation_node]
        if len(parent) > 1:
            raise Exception("More than one parent node")

        children_df = df[pd.notnull(df['ParentNodeID'])]
        if children_df.empty:
            # only for precondition, with one row
            if df.shape[0]==1 and df['IsLeaf'].tolist()[0]:
                OperandReference.get_ml(session, operation_node)
            return operation_node
        for index, row in children_df.iterrows():
            p=None
            p_node_value = row['ParentNodeID']
            for elto in aux_list:
                if elto.NodeID == p_node_value:
                    p = elto
                    break

            # p = [elto for elto in aux_list if elto.NodeID == p_node_value][0]
            op_c= OperationNode(
                OperatorID=row['OperatorID'],
                OperationVID=row['OperationVID'],
                parent=p,
                Scalar=row['Scalar'],
                UseIntervalArithmetics=row['UseIntervalArithmetics'],
                FallbackValue=row['FallbackValue'],
                IsLeaf=row['IsLeaf'],
                ArgumentID=row['ArgumentID'],
                NodeID=row['NodeID']
            )

            aux_list.append(op_c)
            if row['IsLeaf']:
                OperandReference.get_ml(session, op_c)

        return operation_node

    def __eq__(self, other) -> bool:
        """
        Method to compare two OperationNodes
        :param other: OperationNode to compare
        :return: True if they are equal, False otherwise
        """
        attributes = [
            'OperationVID', 'ParentNodeID', 'OperatorID', 'ArgumentID', 'AbsoluteTolerance',\
            'RelativeTolerance', 'FallbackValue', 'UseIntervalArithmetics', 'OperandType', 'IsLeaf', 'Scalar'
        ]
        not_check = ['NodeID']
        if isinstance(other, OperationNode):
            for at in attributes:
                if at =="Scalar" and self.get_attribute(at) and other.get_attribute(at):
                    try:
                        float(self.get_attribute(at))
                        float(other.get_attribute(at))
                        is_float = True
                    except ValueError:
                        is_float = False
                    if is_float:
                        if float(self.get_attribute(at)) != float(other.get_attribute(at)):
                            return False
                    else:
                        self_attribute = self.get_attribute(at)
                        other_attribute = other.get_attribute(at)
                        if self_attribute.lower() in ("true", "false") and self_attribute.lower() == other_attribute.lower():
                            continue
                        if self_attribute != other_attribute:
                            return False
                    continue

                if self.get_attribute(at) != other.get_attribute(at):
                    return False
            if not self.get_attribute('IsLeaf'):
                if self.children and other.children:
                    if len(self.children) != len(other.children):
                        return False
                    # Ordering the children by ArgumentID, it is the only way to compare them
                    self_children = sorted(self.children, key=lambda x: x.ArgumentID)
                    other_children = sorted(other.children, key=lambda x: x.ArgumentID)
                    for index, child in enumerate(self_children):
                        if child != other_children[index]:
                            return False
            else:
                if len(self.operand_reference) != len(other.operand_reference):
                    return False

                sorting_function = lambda x: (x.VariableID if x.VariableID else x.ItemID, x.x, x.y, x.z)
                # We need to order by VariableID, if not available we use ItemID
                other_references = sorted(other.operand_reference, key=sorting_function)
                self_references = sorted(self.operand_reference, key=sorting_function)
                for index, operand in enumerate(self_references):
                    if operand != other_references[index]:
                        return False
            return True
        return False

    def get_attribute(self, at:str):
        types_dict = {
            'NodeID': int,
            'OperationVID': str,
            'ParentNodeID': int,
            'OperatorID': int,
            'ArgumentID': int,
            'AbsoluteTolerance': str,
            'RelativeTolerance': str,
            'FallbackValue': str,
            'UseIntervalArithmetics': bool,
            'OperandType': str,
            'IsLeaf': bool,
            'Scalar': str
        }
        atrib = getattr(self, at)
        if atrib is None:
            return None
        elif pd.isnull(atrib):
            return None
        else:
            return types_dict[at](atrib)


class OperandReference(Base):
    __tablename__ = "OperandReference"

    OperandReferenceID = Column(
        Integer,
        primary_key=True
    )

    NodeID = Column(
        Integer,
        ForeignKey('OperationNode.NodeID')
    )

    x = Column(Integer, nullable=True)
    y = Column(Integer, nullable=True)
    z = Column(Integer, nullable=True)

    OperandReference = Column(String, nullable=True)
    VariableID = Column(Integer, nullable=True)
    ItemID = Column(Integer, nullable=True)
    PropertyID = Column(Integer, nullable=True)

    op_node = relationship("OperationNode", back_populates="operand_reference")
    op_ref_location = relationship("OperandReferenceLocation", back_populates="op_reference")

    @classmethod
    def get_ml(cls, session, operation_node:OperationNode):
        node_id = int(operation_node.NodeID)
        query = session.query(cls).filter(cls.NodeID == node_id)
        df = pd.read_sql_query(query.statement, session.connection(close_with_result=True))
        for index, row in df.iterrows():
            OperandReference(
                NodeID=operation_node.NodeID,
                x=row['x'],
                y=row['y'],
                z=row['z'],
                OperandReference=row['OperandReference'],
                VariableID=row['VariableID'],
                ItemID=row['ItemID'],
                PropertyID=row['PropertyID'],
                op_node=operation_node
            )
        return

    def __eq__(self, other) -> bool:
        """
        Method to compare two OperandReferences
        :param other: OperandReference to compare
        :return: True if they are equal, False otherwise
        """
        attributes = ['OperandReferenceID', 'x', 'y', 'z', 'OperandReference', 'VariableID', 'ItemID', 'PropertyID']
        not_check = ['NodeID']
        if isinstance(other, OperandReference):
            for at in attributes:
                if self.get_attribute(at) != other.get_attribute(at):
                    return False
            # # TODO: In the case we need to check the location
            # if self.op_ref_location and other.op_ref_location:
            #     if len(self.op_ref_location) != len(other.op_ref_location):
            #         return False
            #     for index, location in enumerate(self.op_ref_location):
            #         if location != other.op_ref_location[index]:
            #             return False
            return True
        return False

    def get_attribute(self, at:str):
        types_dict = {
            'OperandReferenceID': int,
            'NodeID': int,
            'x': int,
            'y': int,
            'z': int,
            'OperandReference': str,
            'VariableID': int,
            'ItemID': int,
            'PropertyID': int
        }
        atrib = getattr(self, at)
        if atrib is None:
            return None
        elif pd.isnull(atrib):
            return None
        else:
            return types_dict[at](atrib)


class OperandReferenceLocation(Base):
    __tablename__ = "OperandReferenceLocation"

    OperandReferenceID = Column(
        Integer,
        ForeignKey('OperandReference.OperandReferenceID'),
        primary_key=True
    )
    CellID = Column(Integer, nullable=False)

    Table = Column(String(4))
    Row = Column(String(4))
    column = Column('Column', String(4))
    Sheet = Column(String(4), nullable=True)

    op_reference = relationship("OperandReference", back_populates="op_ref_location")

    def __eq__(self, other) -> bool:  # TODO: Check if we need this for ml_generation, actually we don't want to use this
        if isinstance(other, OperandReferenceLocation):
            return True
        return False

    @classmethod
    def get_operand_reference_location(cls, session, operand_reference_ids):
        query = session.query(cls).filter(cls.OperandReferenceID.in_(operand_reference_ids))
        return pd.read_sql_query(query.statement, session.connection(close_with_result=True))

    @classmethod
    def get_table(cls, session, operand_reference_id):
        query = session.query(cls.Table).filter(cls.OperandReferenceID == operand_reference_id)
        return pd.read_sql_query(query.statement, session.connection(close_with_result=True))

    @classmethod
    def get_cell_id(cls, session, operand_reference_id):
        query = session.query(cls.CellID).filter(cls.OperandReferenceID == operand_reference_id)
        return pd.read_sql_query(query.statement, session.connection(close_with_result=True))


class Operator(Base):
    __tablename__ = "Operator"

    OperatorID = Column(
        Integer,
        primary_key=True
    )

    Name = Column(String(50), nullable=False, unique=True)
    Symbol = Column(String(5), nullable=False, unique=False)
    Type = Column(String(20), nullable=False)

    op_arguments = relationship("OperatorArgument", back_populates="operator")

    @classmethod
    def get_operators(cls, session):
        query = session.query(cls)
        return pd.read_sql_query(query.statement, session.connection(close_with_result=True))

    @classmethod
    def get_operator_symbol(cls, session, name):
        query = session.query(cls.Symbol).filter(cls.Name == name)
        return query.one()[0]


class OperatorArgument(Base):
    __tablename__ = "OperatorArgument"

    ArgumentID = Column(
        Integer,
        primary_key=True
    )

    Order = Column(Integer, nullable=False)
    OperatorID = Column(Integer, ForeignKey('Operator.OperatorID'), nullable=False)
    IsMandatory = Column(Boolean, nullable=False)
    Name = Column(String(50), nullable=False, unique=False)

    operator = relationship("Operator", back_populates="op_arguments")

    @classmethod
    def get_arguments(cls, session):
        query = session.query(cls)
        return pd.read_sql_query(query.statement, session.connection(close_with_result=True))


class TableGroup(Base):
    __tablename__ = "TableGroup"

    TableGroupID = Column(
        Integer,
        primary_key=True
    )

    Code = Column(NVARCHAR, nullable=True, unique=False)
    Name = Column(NVARCHAR, nullable=True, unique=False)
    Description = Column(NVARCHAR, nullable=True, unique=False)
    Type = Column(NVARCHAR, nullable=False, unique=False)
    ParentTableGroupID = Column(Integer, nullable=True, unique=False)

    RowGUID = Column(UUID(as_uuid=True), nullable=False)

    table_group_compositions = relationship('TableGroupComposition', back_populates='table_group')

    @classmethod
    def get_group_from_code(cls, session, group_code):
        group = session.query(cls).filter(TableGroup.Code == group_code).first()
        return group


class TableGroupComposition(Base):
    __tablename__ = "TableGroupComposition"

    TableGroupID = Column(Integer, ForeignKey('TableGroup.TableGroupID'), primary_key=True)
    TableID = Column(Integer, ForeignKey('Table.TableID'), primary_key=True)
    Order = Column(Integer, nullable=True, unique=False)
    StartReleaseID = Column(Integer, nullable=False, unique=False)
    EndReleaseID = Column(Integer, nullable=True, unique=False)

    RowGUID = Column(UUID(as_uuid=True), nullable=False)

    table_group = relationship('TableGroup', back_populates='table_group_compositions')
    table = relationship('Table', back_populates='table_group_compositions')

    @classmethod
    def get_from_parent_table_code(cls, code, session):
        subquery_code = select(TableGroup.TableGroupID).filter(TableGroup.Code == code)
        subquery_parent = select(TableGroup.TableGroupID).filter(TableGroup.ParentTableGroupID.in_(subquery_code))
        query = session.query(cls.TableID, Table.IsAbstract).filter(cls.TableGroupID.in_(subquery_parent))
        query = query.join(Table, Table.TableID == cls.TableID)

        result = query.all()
        return result


class Concept(Base):
    __tablename__ = "Concept"

    ConceptGUID = Column(UUID(as_uuid=True), primary_key=True)
    ClassID = Column(Integer, nullable=False, unique=False)
    OwnerID = Column(Integer, nullable=True, unique=False)


class RelatedConcept(Base):
    __tablename__ = "RelatedConcept"

    ConceptGUID = Column(UUID(as_uuid=True), primary_key=True)
    ConceptRelationID = Column(Integer, primary_key=True)
    IsRelatedConcept = Column(Boolean, nullable=False, unique=False)
    RowGUID = Column(UUID(as_uuid=True), nullable=False)


class ConceptRelation(Base):
    __tablename__ = "ConceptRelation"

    ConceptRelationID = Column(Integer, primary_key=True)
    Type = Column(NVARCHAR, nullable=False, unique=False)
    RowGUID = Column(UUID(as_uuid=True), nullable=False)


class Table(Base):
    __tablename__ = "Table"

    TableID = Column(
        Integer,
        primary_key=True
    )

    IsAbstract = Column(Boolean, nullable=False, unique=False)

    HasOpenColumns = Column(Boolean, nullable=False, unique=False)
    HasOpenRows = Column(Boolean, nullable=False, unique=False)
    HasOpenSheets = Column(Boolean, nullable=False, unique=False)

    IsNormalised = Column(Boolean, nullable=False, unique=False)
    IsFlat = Column(Boolean, nullable=False, unique=False)

    RowGUID = Column(UUID(as_uuid=True), nullable=False)

    table_group_compositions = relationship('TableGroupComposition', back_populates='table')
    table_versions = relationship('TableVersion', back_populates='table')

    module_version_composition = relationship('ModuleVersionComposition', back_populates='table')


class TableVersion(Base):
    __tablename__ = "TableVersion"

    TableVID = Column(
        Integer,
        primary_key=True
    )

    Code = Column(NVARCHAR, nullable=False)
    Name = Column(NVARCHAR, nullable=False)
    TableID = Column(Integer, ForeignKey('Table.TableID'), nullable=False)
    AbstractTableID = Column(Integer, nullable=True)

    KeyID = Column(Integer, nullable=True, unique=False)
    PropertyID = Column(Integer, nullable=True, unique=False)
    ContextID = Column(Integer, nullable=True, unique=False)

    StartReleaseID = Column(Integer, nullable=False, unique=False)
    EndReleaseID = Column(Integer, nullable=True, unique=False)

    RowGUID = Column(UUID(as_uuid=True), nullable=False)

    table = relationship('Table', back_populates='table_versions')
    module_version_composition = relationship('ModuleVersionComposition', back_populates='table_version')
    table_version_cells = relationship('TableVersionCell', back_populates='table_version')

    @classmethod
    def get_tables_versions_of_table_group_compositions(cls, session, table_id, is_abstract, release_id):

        query = session.query(cls)
        if is_abstract:
            query = query.filter(cls.AbstractTableID == table_id)
        else:
            query = query.filter(cls.TableID == table_id)
        query = filter_by_release(query, cls.StartReleaseID, cls.EndReleaseID, release_id)
        return query.all()

    @classmethod
    def check_table_exists(cls, session, table_code, release_id):
        query = session.query(cls.TableVID).filter_by(Code=table_code)
        query = filter_by_release(query, cls.StartReleaseID, cls.EndReleaseID, release_id)
        return query.one_or_none() is not None

    @classmethod
    def get_all(cls, session):
        query = session.query(cls)
        df = pd.read_sql_query(query.statement, session.connection(close_with_result=True)).rename(columns={'TableVID': TABLE_VERSION_ID})
        return df

    @classmethod
    def get_table_code(cls, session, table_vid):
        query = session.query(cls.Code).filter(cls.TableVID == table_vid)
        return query.one()


class ModuleVersion(Base):
    __tablename__ = "ModuleVersion"

    ModuleVID = Column(Integer, primary_key=True)
    ModuleID = Column(Integer, nullable=False, unique=False)
    Code = Column(NVARCHAR(30), nullable=False, unique=False)

    GlobalKeyID = Column(Integer, nullable=True, unique=False)

    StartReleaseID = Column(Integer, nullable=False, unique=False)
    EndReleaseID = Column(Integer, nullable=True, unique=False)

    Name = Column(String(100), nullable=False, unique=False)
    Description = Column(String(255), nullable=True, unique=False)
    VersionNumber = Column(String(20), nullable=True, unique=False)

    FromReferenceDate = Column(Date, nullable=False, unique=False)
    ToReferenceDate = Column(Date, nullable=True, unique=False)

    RowGUID = Column(UUID(as_uuid=True), nullable=False)

    module_version_compositions = relationship('ModuleVersionComposition', back_populates="module_version")
    operation_scope_compositions = relationship('OperationScopeComposition', back_populates="module_version")

    @classmethod
    def get_from_date_from_vid(cls, session, module_vid):
        query = session.query(cls.FromReferenceDate).filter_by(ModuleVID=module_vid)
        return query.one()[0]

    @classmethod
    def get_from_tables_vids(cls, session, tables_vids, only_last_release=True):
        query = session.query(cls.ModuleVID, cls.FromReferenceDate, cls.ToReferenceDate, ModuleVersionComposition.TableVID)
        query = query.join(ModuleVersionComposition, and_(ModuleVersionComposition.ModuleVID == cls.ModuleVID,
                                                          ModuleVersionComposition.TableVID.in_(tables_vids)))

        if only_last_release:
            query = query.filter(cls.EndReleaseID.is_(None))
        return pd.read_sql_query(query.statement, session.connection(close_with_result=True))

    @classmethod
    def get_module_version_id(cls, session, code, ref_date):
        query = session.query(cls.ModuleVID).filter_by(Code=code)
        query = filter_by_date(query, cls.FromReferenceDate, cls.ToReferenceDate, ref_date)

        return query.one()

    @classmethod
    def get_module_version_ids(cls, session, code):
        query = session.query(cls.ModuleVID, cls.FromReferenceDate, cls.ToReferenceDate).filter_by(Code=code)

        return list(query.all())

    @classmethod
    def get_all_module_codes(cls, session):
        query = session.query(cls.Code).distinct()
        return [code for code, in query.all()]

    @classmethod
    def get_precondition_module_versions(cls, session, precondition_items):
        query = session.query(cls.ModuleVID, cls.FromReferenceDate, cls.ToReferenceDate, VariableVersion.VariableVID,
                              VariableVersion.Code)
        query = query.join(ModuleParameters, ModuleParameters.ModuleVID == cls.ModuleVID)
        query = query.join(VariableVersion, and_(VariableVersion.VariableVID == ModuleParameters.VariableVID,
                                                 VariableVersion.Code.in_(precondition_items)))
        query = query.join(Variable,
                           and_(Variable.VariableID == VariableVersion.VariableID, Variable.Type == FILING_INDICATOR))

        return pd.read_sql_query(query.statement, session.connection(close_with_result=True))

    @classmethod
    def get_module_version_by_vid(cls, session, vid):
        query = session.query(cls).filter_by(ModuleVID=vid)
        return pd.read_sql_query(query.statement, session.connection(close_with_result=True))


class ModuleParameters(Base):
    __tablename__ = "ModuleParameters"

    ModuleVID = Column(Integer, ForeignKey('ModuleVersion.ModuleVID'), primary_key=True)
    VariableVID = Column(Integer, primary_key=True)
    RowGUID = Column(UUID(as_uuid=True), nullable=False)


class ModuleVersionComposition(Base):
    __tablename__ = "ModuleVersionComposition"

    ModuleVID = Column(Integer, ForeignKey('ModuleVersion.ModuleVID'), primary_key=True)
    TableID = Column(Integer, ForeignKey('Table.TableID'), primary_key=True)

    TableVID = Column(Integer, ForeignKey('TableVersion.TableVID'), nullable=False, unique=False)
    Order = Column(Integer, nullable=True, unique=False)

    RowGUID = Column(UUID(as_uuid=True), nullable=False)

    table = relationship('Table', back_populates='module_version_composition')
    table_version = relationship('TableVersion', back_populates='module_version_composition')
    module_version = relationship('ModuleVersion', back_populates="module_version_compositions")

    @classmethod
    def get_modules_from_table_ids(cls, session, table_ids, release_id):
        modules_query = session.query(cls.ModuleVID, cls.TableID, ModuleVersion.Code.label('module_code')).join(
            ModuleVersion, ModuleVersion.ModuleVID == cls.ModuleVID)

        modules_query = filter_by_release(modules_query, ModuleVersion.StartReleaseID, ModuleVersion.EndReleaseID,
                                          release_id)
        modules_query.filter(cls.TableID.in_(table_ids))

        modules_df = pd.read_sql(sql=modules_query.statement, con=session.bind)
        return modules_df


class Item(Base):
    __tablename__ = "Item"

    ItemID = Column(Integer, primary_key=True)
    Name = Column(NVARCHAR, nullable=False, unique=False)
    Description = Column(NVARCHAR, nullable=True, unique=False)
    IsCompound = Column(Boolean, nullable=False, unique=False)
    IsProperty = Column(Boolean, nullable=False, unique=False)
    IsActive = Column(Boolean, nullable=False, unique=False)
    RowGUID = Column(UUID(as_uuid=True), nullable=False)


class ItemCategory(Base):
    __tablename__ = "ItemCategory"

    ItemID = Column(
        Integer,
        primary_key=True
    )

    StartReleaseID = Column(
        Integer,
        primary_key=True
    )

    CategoryID = Column(Integer, nullable=False, unique=False)
    Code = Column(NVARCHAR, nullable=False, unique=False)
    IsDefaultItem = Column(Integer, nullable=False, unique=False)
    Signature = Column(NVARCHAR, nullable=False, unique=False)
    EndReleaseID = Column(Integer, nullable=True, unique=False)

    RowGUID = Column(UUID(as_uuid=True), nullable=False)

    @classmethod
    def get_item_category_from_code(cls, code, session, release_id):
        query = session.query(cls).filter(cls.Code == code)
        query = filter_by_release(query, cls.StartReleaseID, cls.EndReleaseID, release_id)
        return query.first()

    @classmethod
    def get_items(cls, session, item_codes, release_id):
        query = session.query(cls.Signature).filter(cls.Signature.in_(item_codes))
        query = filter_by_release(query, cls.StartReleaseID, cls.EndReleaseID, release_id)
        data = pd.read_sql_query(query.statement, session.connection(close_with_result=True))
        return data

    @classmethod
    def get_default_item(cls, session, category_id, release_id):
        query = session.query(cls.ItemID).filter(and_(cls.CategoryID == category_id, cls.IsDefaultItem == 1))
        query = filter_by_release(query, cls.StartReleaseID, cls.EndReleaseID, release_id)
        return query.first()

    @classmethod
    def get_item_category_id_from_signature(cls, signature, session):
        query = session.query(cls.ItemID).filter(cls.Signature == signature)
        # query = filter_by_release(query, cls.StartReleaseID, cls.EndReleaseID, release_id)
        return query.first()

    @classmethod
    def get_property_from_code(cls, code, session, release_id = None):
        query = session.query(cls).filter(cls.Code == code)
        query = query.join(Item, and_(Item.ItemID == cls.ItemID, Item.IsProperty == 1))
        if release_id:
            query = filter_by_release(query, cls.StartReleaseID, cls.EndReleaseID, release_id)
        return query.first()

    @classmethod
    def get_property_from_signature(cls, signature, session, release_id = None):
        query = session.query(cls).filter(cls.Signature == signature)
        query = query.join(Item, and_(Item.ItemID == cls.ItemID, Item.IsProperty == 1))
        if release_id:
            query = filter_by_release(query, cls.StartReleaseID, cls.EndReleaseID, release_id)
        return query.one_or_none()

    @classmethod
    def get_property_id_from_code(cls, code, session):
        query = session.query(cls.ItemID).filter(cls.Code == code)
        # query = filter_by_release(query, cls.StartReleaseID, cls.EndReleaseID, release_id)
        return query.first()

    @classmethod
    def get_item_category_from_id(cls, session, item_id):
        query = session.query(cls).filter(cls.ItemID == item_id)
        return query.first()


class Variable(Base):
    __tablename__ = "Variable"

    VariableID = Column(Integer, primary_key=True)
    Type = Column(String(20), nullable=False)
    RowGUID = Column(UUID(as_uuid=True))


class VariableVersion(Base):
    __tablename__ = "VariableVersion"
    VariableVID = Column(Integer, primary_key=True)
    VariableID = Column(Integer, nullable=False)
    PropertyID = Column(Integer, ForeignKey('Property.PropertyID'), nullable=False)
    SubCategoryVID = Column(Integer)
    ContextID = Column(Integer, ForeignKey('Context.ContextID'))
    KeyID = Column(Integer)
    IsMultiValued = Column(Integer)
    Code = Column(NVARCHAR(20))
    Name = Column(NVARCHAR(50))
    StartReleaseID = Column(Integer, nullable=False)
    EndReleaseID = Column(Integer)
    RowGUID = Column(UUID(as_uuid=True))

    property = relationship('Property', back_populates='variable_versions')
    context = relationship('Context', back_populates='variable_versions')
    table_version_cells = relationship('TableVersionCell', back_populates='variable_versions')

    @classmethod
    def check_variable_exists(cls, session, variable_name, release_id):
        query = session.query(cls).filter_by(Code=variable_name)
        query = filter_by_release(query, cls.StartReleaseID, cls.EndReleaseID, release_id)
        return query.one_or_none() is not None

    @classmethod
    def check_precondition(cls, session, variable_name, release_id):  # TODO: Change name
        query = session.query(cls).filter_by(Code=variable_name)
        query = filter_by_release(query, cls.StartReleaseID, cls.EndReleaseID, release_id)
        return query.one_or_none()

    @classmethod
    def get_all_preconditions(cls, session, release_id):
        query = session.query(cls).filter(cls.Code.isnot(None))
        query = filter_by_release(query, cls.StartReleaseID, cls.EndReleaseID, release_id)
        return query.all()

    @classmethod
    def get_VariableID(cls, session, variable_name, release_id):
        query = session.query(cls.VariableID).filter_by(Code=variable_name)
        query = filter_by_release(query, cls.StartReleaseID, cls.EndReleaseID, release_id)
        return query.one_or_none()

    @classmethod
    def get_Variable_info(cls, session, variable_vid):
        query = session.query(cls).filter(cls.VariableVID==variable_vid)
        variable = pd.read_sql_query(query.statement, session.connection(close_with_result=True)).to_dict(orient='records')
        return variable

    @classmethod
    def get_contexts_of_variables(cls, session, context_ids, release_id):
        results = []
        batch_size = 2000
        batch_start = 0

        while batch_start < len(context_ids):
            batch_end = batch_start + batch_size
            context_batch = context_ids[batch_start:batch_end]

            query = session.query(cls.VariableVID.label('variable_vid'), cls.PropertyID.label('variable_property_id'),
                                  ContextComposition.PropertyID.label('context_property'),
                                  ContextComposition.ItemID.label('context_item')).filter(cls.ContextID.in_(context_batch)).join(
                (ContextComposition, ContextComposition.ContextID == cls.ContextID))
            query = filter_by_release(query, cls.StartReleaseID, cls.EndReleaseID, release_id)

            results.append(pd.read_sql_query(query.statement, session.connection(close_with_result=True)))
            batch_start += batch_size

        data = pd.concat(results, axis=0)
        return data


class Operation(Base):
    __tablename__ = 'Operation'

    OperationID = Column(Integer, primary_key=True)
    Code = Column(NVARCHAR, nullable=False, unique=False)
    Type = Column(NVARCHAR, nullable=False, unique=False)
    Source = Column(NVARCHAR, nullable=False, unique=False)

    GroupOperID = Column(Integer, nullable=True, unique=False)

    RowGUID = Column(UUID(as_uuid=True))

    @classmethod
    def get_operations_from_codes(cls, session, operation_codes, release_id=None):
        query = session.query(cls.Code, OperationVersion.OperationVID).join(OperationVersion,
                                                                            OperationVersion.OperationID == cls.OperationID)
        query = filter_by_release(query, start_release=OperationVersion.StartReleaseID,
                                  end_release=OperationVersion.EndReleaseID, release_id=release_id)
        query = query.filter(
            and_(cls.Code.in_(operation_codes), cls.Type == 'calculation'))
        data = pd.read_sql_query(query.statement, session.connection(close_with_result=True))
        return data

class OperationVersion(Base):
    __tablename__ = 'OperationVersion'

    OperationVID = Column(Integer, primary_key=True)

    OperationID = Column(Integer, nullable=False, unique=False)
    PreconditionOperationVID = Column(Integer, nullable=True, unique=False)
    SeverityOperationVID = Column(Integer, nullable=True, unique=False)
    StartReleaseID = Column(Integer, nullable=False, unique=False)
    EndReleaseID = Column(Integer, nullable=True, unique=False)
    Expression = Column(NVARCHAR, nullable=False, unique=False)
    Description = Column(NVARCHAR(1000), nullable=True, unique=False)

    RowGUID = Column(UUID(as_uuid=True))

    operation_scopes = relationship('OperationScope', back_populates="operation_version")


    @classmethod
    def get_operations_from_code(cls, session, code, release_id=None):
        query = session.query(cls, Operation.Code).join(Operation, Operation.OperationID == cls.OperationID)
        query = query.filter(Operation.Code == code)
        data = pd.read_sql_query(query.statement, session.connection(close_with_result=True))
        return data

    @classmethod
    def get_operation_version(cls, session, operation_vid):
        query = session.query(cls).filter(cls.OperationVID == operation_vid)
        data = pd.read_sql_query(query.statement, session.connection(close_with_result=True))
        return data

    @classmethod
    def get_expressions_from_table_code(cls, session, table_code, only_on_with=True,
                                        only_automatic=True):
        query = session.query(cls.Expression, Operation.Code, Operation.Source).distinct().join(
            Operation, Operation.OperationID == cls.OperationID)
        if isinstance(table_code, list):
            query = query.filter(or_(*[cls.Expression.like(f"%t{t}%") for t in table_code]))
        else:
            aux = table_code.replace("_", "/_")
            if only_on_with:
                query = query.filter(cls.Expression.like(f"with%t{aux}%}}:%", escape="/"))
            else:
                query = query.filter(cls.Expression.like(f"%t{aux}%"))

        # Automatic rules only
        if only_automatic:
            query = query.filter(Operation.Source.in_(["sign", "existence", "hierarchy"]))
        result = query.all()
        result_dict = {r[1]: r[0] for r in result}
        return result_dict


class TableVersionCell(Base):
    __tablename__ = 'TableVersionCell'

    TableVID = Column(Integer, ForeignKey("TableVersion.TableVID"), primary_key=True)
    CellID = Column(Integer, primary_key=True)
    CellCode = Column(NVARCHAR(100), nullable=True)
    IsNullable = Column(Boolean, nullable=False)
    IsExcluded = Column(Boolean, nullable=False)
    IsVoid = Column(Boolean, nullable=False)
    Sign = Column(NVARCHAR(3), nullable=True)
    variableVID = Column(Integer, ForeignKey("VariableVersion.VariableVID"), nullable=True)

    RowGUID = Column(UUID(as_uuid=True))

    table_version = relationship('TableVersion', back_populates="table_version_cells")
    variable_versions = relationship('VariableVersion', back_populates='table_version_cells')

    @classmethod
    def get_sign_query(cls, session, sign):
        query = session.query(cls.TableVID).join(TableVersion, TableVersion.TableVID==cls.TableVID).filter(TableVersion.Code.in_(sign))
        table_vid = pd.read_sql_query(query.statement, session.connection(close_with_result=True))["TableVID"].unique().tolist()
        query = session.query(cls).filter(cls.TableVID.in_(table_vid))#.update({"Sign": "neg"}).distinct().all()

        return query.distinct().all()#query.all()

    @classmethod
    def get_signed_tables(cls, session, release_id):
        # query = session.query(cls.TableVID).join(TableVersion, TableVersion.TableVID==cls.TableVID).filter(cls.Sign.isnot(None)).distinct().all()
        query = session.query(cls.TableVID).join(TableVersion, TableVersion.TableVID==cls.TableVID).filter(cls.Sign.is_not(None)).distinct()
        query = filter_by_release(query, TableVersion.StartReleaseID, TableVersion.EndReleaseID, release_id)
        return pd.read_sql_query(query.statement, session.connection(close_with_result=True))

    @classmethod
    def get_not_nullable_tables(cls, session, release_id):
        query = session.query(cls.TableVID).join(TableVersion, TableVersion.TableVID==cls.TableVID).filter(cls.IsNullable==0).distinct()
        query = filter_by_release(query, TableVersion.StartReleaseID, TableVersion.EndReleaseID, release_id)
        return pd.read_sql_query(query.statement, session.connection(close_with_result=True))

    @classmethod
    def get_from_table_vid_with_sign(cls, session, table_vid):
        query = session.query(cls.CellID, cls.Sign, cls.TableVID).filter(cls.TableVID == table_vid)
        query = query.filter(cls.Sign.is_not(None)).distinct()
        return pd.read_sql_query(query.statement, session.connection())


class Category(Base):
    __tablename__ = 'Category'

    CategoryID = Column(Integer, primary_key=True)
    Code = Column(NVARCHAR, nullable=False, unique=False)

    Name = Column(NVARCHAR, nullable=False, unique=False)
    Description = Column(NVARCHAR, nullable=True, unique=False)

    IsEnumerated = Column(Boolean, nullable=False, unique=False)
    IsSuperCategory = Column(Boolean, nullable=False, unique=False)
    IsActive = Column(Boolean, nullable=False, unique=False)
    IsExternalRefData = Column(Boolean, nullable=False, unique=False)

    RefDataSource = Column(NVARCHAR, nullable=True, unique=False)
    RowGUID = Column(UUID(as_uuid=True), nullable=False)

    subcategories = relationship('SubCategory', back_populates='category')
    property_categories = relationship('PropertyCategory', back_populates='category')

    @classmethod
    def get_from_code(cls, session, category_code):
        query = session.query(cls).filter(cls.Code == category_code)
        return query.first()

    @classmethod
    def get_from_id(cls, session, category_id):
        query = session.query(cls).filter(cls.CategoryID == category_id)
        return query.first()


class SubCategory(Base):
    __tablename__ = 'SubCategory'

    SubCategoryID = Column(Integer, primary_key=True)
    CategoryID = Column(Integer, ForeignKey('Category.CategoryID'), nullable=False, unique=False)

    Code = Column(NVARCHAR, nullable=False, unique=False)
    Name = Column(NVARCHAR, nullable=True, unique=False)
    Description = Column(NVARCHAR, nullable=True, unique=False)

    RowGUID = Column(UUID(as_uuid=True), nullable=False)

    category = relationship('Category', back_populates='subcategories')
    subcategory_versions = relationship('SubCategoryVersion', back_populates='subcategory')

    @classmethod
    def filter_by_code(cls, session, code, release_id):
        query = session.query(cls).filter_by(Code=code).join(SubCategoryVersion,
                                                             SubCategoryVersion.SubCategoryID == cls.SubCategoryID)
        query = filter_by_release(query, SubCategoryVersion.StartReleaseID, SubCategoryVersion.EndReleaseID, release_id)
        return query.first()

    @classmethod
    def filter_by_id(cls, session, subcategory_id, release_id):
        query = session.query(cls).filter_by(SubCategoryID=subcategory_id).join(SubCategoryVersion,
                                                             SubCategoryVersion.SubCategoryID == cls.SubCategoryID)
        query = filter_by_release(query, SubCategoryVersion.StartReleaseID, SubCategoryVersion.EndReleaseID, release_id)
        return query.first()

    @classmethod
    def get_codes(cls, session):
        return session.query(cls.Code).all()

    @classmethod
    def get_all(cls, session):
        return session.query(cls).all()

    @classmethod
    def get_code_from_id(cls, session, subcategory_id):
        query = session.query(cls.Code).filter(cls.SubCategoryID == subcategory_id)
        code = pd.read_sql_query(query.statement, session.connection(close_with_result=True))["Code"].tolist()
        return code

    @classmethod
    def get_subcategories_codes_from_category_id(cls, session, category_id):
        query = session.query(cls.Code).filter(cls.CategoryID == category_id)
        code = pd.read_sql_query(query.statement, session.connection(close_with_result=True))["Code"].tolist()
        return code


class SubCategoryVersion(Base):
    __tablename__ = 'SubCategoryVersion'

    SubCategoryVID = Column(Integer, primary_key=True)
    SubCategoryID = Column(Integer, ForeignKey('SubCategory.SubCategoryID'), nullable=False, unique=False)
    StartReleaseID = Column(Integer, nullable=False, unique=False)
    EndReleaseID = Column(Integer, nullable=True, unique=False)

    RowGUID = Column(UUID(as_uuid=True), nullable=False)

    subcategory = relationship('SubCategory', back_populates='subcategory_versions')
    subcategory_items = relationship('SubCategoryItem', back_populates='subcategory_version')


class SubCategoryItem(Base):
    __tablename__ = 'SubCategoryItem'

    ItemID = Column(Integer, primary_key=True)
    SubCategoryVID = Column(Integer, ForeignKey('SubCategoryVersion.SubCategoryVID'), primary_key=True)

    Order = Column(Integer, nullable=True, unique=False)
    Label = Column(NVARCHAR, nullable=True, unique=False)

    ParentItemID = Column(Integer, nullable=True, unique=False)
    ComparisonOperatorID = Column(Integer, nullable=True, unique=False)
    ArithmeticOperatorID = Column(Integer, nullable=True, unique=False)

    RowGUID = Column(UUID(as_uuid=True), nullable=False)

    subcategory_version = relationship('SubCategoryVersion', back_populates='subcategory_items')

    @classmethod
    def get_from_subcategory_code(cls, session, subcategory_code, release_id):
        query = session.query(cls, ItemCategory.IsDefaultItem).join(ItemCategory, ItemCategory.ItemID == cls.ItemID)
        query = query.join(SubCategoryVersion, SubCategoryVersion.SubCategoryVID == cls.SubCategoryVID)
        query = filter_by_release(query, SubCategoryVersion.StartReleaseID, SubCategoryVersion.EndReleaseID, release_id)
        query = query.join(SubCategory,
                           and_(SubCategory.SubCategoryID == SubCategoryVersion.SubCategoryID, SubCategory.Code == subcategory_code))
        return pd.read_sql_query(query.statement, session.connection(close_with_result=True))

    @classmethod
    def get_item_from_subcategory_and_parent(cls, session, subcategory_id, parent_id):
        query = session.query(cls.ItemID, ItemCategory.IsDefaultItem).join(ItemCategory, ItemCategory.ItemID == cls.ItemID)
        query = query.filter(and_(cls.SubCategoryVID == subcategory_id, cls.ParentItemID == parent_id))
        items_id = pd.read_sql_query(query.statement, session.connection(close_with_result=True))['ItemID'].tolist()
        result_dict = {}
        result_dict['parent_id'] = parent_id
        result_dict['children_id'] = items_id
        return result_dict


class Context(Base):
    __tablename__ = 'Context'

    ContextID = Column(Integer, primary_key=True)
    Signature = Column(NVARCHAR, nullable=False, unique=True)

    RowGUID = Column(UUID(as_uuid=True), nullable=False)

    context_compositions = relationship('ContextComposition', back_populates='context')
    variable_versions = relationship('VariableVersion', back_populates='context')


class ContextComposition(Base):
    __tablename__ = 'ContextComposition'

    ContextID = Column(Integer, ForeignKey('Context.ContextID'), primary_key=True)
    PropertyID = Column(Integer, ForeignKey('Property.PropertyID'), primary_key=True)

    ItemID = Column(Integer, nullable=False, unique=False)
    RowGUID = Column(UUID(as_uuid=True), nullable=False)

    context = relationship('Context', back_populates='context_compositions')
    property = relationship('Property', back_populates='context_compositions')

    @classmethod
    def filter_by_common_context(cls, session, property_id, context_properties, item_ids):
        query = session.query(cls)
        aliased_context = aliased(cls)
        query = query.join(aliased_context, aliased_context.ContextID == cls.ContextID).filter(
            aliased_context.PropertyID != property_id)
        for count in range(len(context_properties)):
            aliased_context = aliased(cls)
            query = query.join(aliased_context, aliased_context.ContextID == cls.ContextID).filter(
                and_(aliased_context.PropertyID == context_properties[count],
                     aliased_context.ItemID == item_ids[count]))

        return pd.read_sql_query(query.statement, session.connection(close_with_result=True))

    @classmethod
    def filter_by_properties(cls, session, properties):
        subquery = session.query(cls.ContextID).filter(cls.PropertyID.in_(properties))
        query = session.query(cls.ContextID.label('context_id'), cls.PropertyID.label('property_id'), cls.ItemID).filter(
            cls.ContextID.in_(subquery))
        data = pd.read_sql_query(query.statement, session.connection(close_with_result=True))
        return data


class PropertyCategory(Base):
    __tablename__ = 'PropertyCategory'

    PropertyID = Column(Integer, ForeignKey('Property.PropertyID'), primary_key=True)
    StartReleaseID = Column(Integer, primary_key=True)

    CategoryID = Column(Integer, ForeignKey('Category.CategoryID'), nullable=False, unique=False)
    EndReleaseID = Column(Integer, nullable=True, unique=False)
    RowGUID = Column(UUID(as_uuid=True), nullable=False)

    category = relationship('Category', back_populates='property_categories')
    property = relationship('Property', back_populates='property_categories')


class Property(Base):
    __tablename__ = 'Property'

    PropertyID = Column(Integer, primary_key=True)

    IsComposite = Column(Boolean, nullable=False, unique=False)
    IsMetric = Column(Boolean, nullable=False, unique=False)

    DataTypeID = Column(Integer, nullable=True, unique=False)
    ValueLength = Column(Integer, nullable=True, unique=False)
    PeriodType = Column(NVARCHAR, nullable=True, unique=False)

    property_categories = relationship('PropertyCategory', back_populates='property')
    variable_versions = relationship('VariableVersion', back_populates='property')

    context_compositions = relationship('ContextComposition', back_populates='property')


# Views
def filter_by_release(query, start_release, end_release, release_id):
    """
    Live Release: EndReleaseID is NULL
    Specific Release: StartReleaseID <= ?  and (EndReleaseID > ? or EndReleaseID is NULL)
    """
    if release_id is None:
        return query.filter(and_(end_release.is_(None), True))
    return query.filter(and_(start_release <= release_id,
                             or_(end_release > release_id,
                                 end_release.is_(None))))


def filter_by_date(query, start_date, end_date, date):
    date = datetime.strptime(date, '%Y-%m-%d')
    if date is None:
        return query.filter(and_(end_date.is_(None), True))

    return query.filter(and_(start_date <= date), or_(end_date > date, end_date.is_(None)))


def filter_elements(query, column, values):
    if len(values) == 1:
        if values[0] == '*':
            return query
        elif '-' in values[0]:
            limits = values[0].split('-')
            return query.filter(column.between(limits[0], limits[1]))
        else:
            return query.filter(column == values[0])
    range_control = any(['-' in x for x in values])
    if not range_control:  # If no range is present, we simply check if values are in DB
        return query.filter(column.in_(values))
    dynamic_filter = []
    for x in values:
        if '-' in x:
            limits = x.split('-')
            dynamic_filter.append(column.between(limits[0], limits[1]))
        else:
            dynamic_filter.append(column == x)

    return query.filter(or_((x for x in dynamic_filter)))


def _check_ranges_values_are_present(data: pd.DataFrame, data_column, values):

    if values is not None and '-' in values[0]:
        test = values[0].split('-')
        if test[0] not in list(data[data_column].values):
            data = pd.DataFrame(columns=data.columns)

        if test[1] not in list(data[data_column].values):
            data = pd.DataFrame(columns=data.columns)
    return data



class ViewDatapoints(Base):
    __tablename__ = "drr_datapoints"

    cell_code = Column(String, primary_key=True)
    table_code = Column(String)
    row_code = Column(String)
    column_code = Column(String)
    sheet_code = Column(String)
    variable_id = Column(String)
    data_type = Column(String)
    table_vid = Column(Integer)
    property_id = Column(Integer)
    start_release = Column(Integer)
    end_release = Column(Integer)
    cell_id = Column(Integer)
    context_id = Column(Integer)
    variable_vid = Column(String)

    @classmethod
    def get_filtered_datapoints(cls, session, table: str, table_info: dict, release_id: int = None):
        mapping_dictionary = {'rows': 'row_code', 'cols': 'column_code', 'sheets': 'sheet_code'}
        conditions = [cls.table_code == table]

        for key, values in table_info.items():
            column = getattr(cls, mapping_dictionary[key])
            if values is not None:
                if '-' in values[0]:
                    low_limit, high_limit = values[0].split('-')
                    conditions.append(column.between(low_limit, high_limit))
                elif values[0] == '*':
                    continue
                else:
                    conditions.append(column.in_(values))

        if release_id:
            conditions.append(cls.release_id == release_id)

        query = session.query(cls).filter(and_(*conditions))

        return pd.read_sql_query(query.statement, session.connection(close_with_result=True))

    @classmethod
    def get_all_datapoints(cls, session):
        query = session.query(cls)
        return pd.read_sql_query(query.statement, session.connection(close_with_result=True))

    @classmethod
    def get_table_data(cls, session, table, rows=None, columns=None, sheets=None, release_id=None):
        query = session.query(cls.cell_code, cls.table_code,
                              cls.row_code, cls.column_code,
                              cls.sheet_code, cls.variable_id,
                              cls.data_type, cls.table_vid, cls.cell_id)
        query = query.filter_by(table_code=table)
        if rows is not None:
            query = filter_elements(query, cls.row_code, rows)
        if columns is not None:
            query = filter_elements(query, cls.column_code, columns)
        if sheets is not None:
            query = filter_elements(query, cls.sheet_code, sheets)
        query = filter_by_release(query, cls.start_release, cls.end_release, release_id)
        data = pd.read_sql_query(query.statement, session.connection())

        data = _check_ranges_values_are_present(data, 'row_code', rows)
        data = _check_ranges_values_are_present(data, 'column_code', columns)
        data = _check_ranges_values_are_present(data, 'sheet_code', sheets)

        return data

    @classmethod
    def get_from_property(cls, session, property_id, release_id=None):
        query = session.query(cls.cell_code, cls.table_code,
                              cls.row_code, cls.column_code,
                              cls.sheet_code, cls.variable_id,
                              cls.data_type, cls.table_vid)
        query = query.filter_by(property_id=property_id)

        query = filter_by_release(query, cls.start_release, cls.end_release, release_id)
        data = pd.read_sql_query(query.statement, session.connection(close_with_result=True))
        return data

    @classmethod
    def get_from_table_vid(cls, session, table_version_id):
        query = session.query(cls)
        query = query.filter(cls.table_vid == table_version_id)
        query = filter_by_release(query, cls.start_release, cls.end_release, release_id=None)
        return pd.read_sql_query(query.statement, session.connection())

    @classmethod
    def get_from_table_code(cls, session, table_code, release_id=None):
        query = session.query(cls)
        query = query.filter(cls.table_code == table_code)
        query = filter_by_release(query, cls.start_release, cls.end_release, release_id)
        return pd.read_sql_query(query.statement, session.connection())

    @classmethod
    def get_from_table_vid_with_is_nullable(cls, session, table_version_id):
        query = session.query(cls, TableVersionCell.IsNullable).join(TableVersionCell, TableVersionCell.CellID == cls.cell_id)
        query = query.filter(cls.table_vid == table_version_id)
        return pd.read_sql_query(query.statement, session.connection())

    @classmethod
    def get_from_subcategory_properties(cls, session, properties, release_id):
        query = session.query(cls.table_code, cls.row_code, cls.column_code, cls.sheet_code, cls.property_id, cls.context_id,
                              cls.variable_vid, ContextComposition.PropertyID.label('subcategory_property'), cls.cell_id, cls.data_type)
        query = query.join(ContextComposition,
                           and_(ContextComposition.ContextID == cls.context_id, ContextComposition.PropertyID.in_(properties)))
        query = filter_by_release(query, cls.start_release, cls.end_release, release_id)
        data = pd.read_sql_query(query.statement, session.connection(close_with_result=True))
        return data

    @classmethod
    def filter_by_context_and_property(cls, session, context, property_key, release_id):
        query = session.query(cls.table_code, cls.row_code, cls.column_code, cls.sheet_code, cls.property_id, cls.context_id,
                              cls.variable_vid, cls.cell_id).filter(cls.context_id == context)
        if property_key:
            query = query.filter(cls.property_id == property_key)
        query = filter_by_release(query, cls.start_release, cls.end_release, release_id)
        data = pd.read_sql_query(query.statement, session.connection(close_with_result=True))
        return data

    @classmethod
    def get_Variable_info_from_cell_id(cls, session, cell_id):
        query = session.query(cls).filter(cls.cell_id==cell_id)
        variable = pd.read_sql_query(query.statement, session.connection(close_with_result=True)).to_dict(orient='records')
        return variable

    @classmethod
    def get_variables_info_from_cell_id_list(cls, session, cell_id_list):
        query = session.query(cls.variable_id).filter(cls.cell_id.in_(cell_id_list))
        variable = pd.read_sql_query(query.statement, session.connection(close_with_result=True))["variable_id"].tolist()
        return variable

    @classmethod
    def get_datapoints_for_properties_validations(cls, session, items_list):
        query = session.query(cls, VariableVersion.KeyID).join(VariableVersion, VariableVersion.VariableVID == cls.variable_vid)
        query = query.filter(cls.property_id.in_(items_list))
        data = pd.read_sql_query(query.statement, session.connection(close_with_result=True))
        return data

    @classmethod
    def get_from_variables(cls, session, variables, release_id=None):
        # Make batches of 1000 variables
        results = []
        batch_size = 1000
        for i in range(0, len(variables), batch_size):
            batch_end = i + batch_size
            variables_batch = variables[i:batch_end]
            query = session.query(cls.variable_vid, cls.cell_code, cls.cell_id, cls.variable_id,
                                  cls.table_code, cls.row_code, cls.column_code, cls.sheet_code)
            query = query.filter(cls.variable_vid.in_(variables_batch))
            query = filter_by_release(query, cls.start_release, cls.end_release, release_id)
            results.append(pd.read_sql_query(query.statement, session.connection(close_with_result=True)))
        data = pd.concat(results, axis=0)
        return data


class ViewKeyComponents(Base):
    __tablename__ = "drr_key_components"

    table_code = Column(String, primary_key=True)
    property_code = Column(String, primary_key=True)
    data_type = Column(String, primary_key=True)
    table_version_id = Column(Integer)
    start_release_ic = Column(Integer)
    end_release_ic = Column(Integer)
    start_release_mv = Column(Integer)
    end_release_mv = Column(Integer)

    @classmethod
    def get_by_table(cls, session, table, release_id):
        query = session.query(cls.table_code, cls.property_code, cls.data_type)
        query = query.filter_by(table_code=table)
        query = filter_by_release(query, cls.start_release_ic, cls.end_release_ic, release_id)
        query = filter_by_release(query, cls.start_release_mv, cls.end_release_mv, release_id)
        data = pd.read_sql_query(query.statement, session.connection(close_with_result=True))
        return data

    @classmethod
    def get_from_several_tables(cls, session, tables, release_id):
        query = session.query(cls.table_code, cls.property_code, cls.data_type)
        query = query.filter(cls.table_code.in_(tables))
        query = filter_by_release(query, cls.start_release_ic, cls.end_release_ic, release_id)
        query = filter_by_release(query, cls.start_release_mv, cls.end_release_mv, release_id)
        data = pd.read_sql_query(query.statement, session.connection(close_with_result=True))
        return data

    @classmethod
    def get_by_table_version_id(cls, session, table_version_id):
        query = session.query(cls.table_code, cls.property_code, cls.data_type)
        query = query.filter_by(table_version_id=table_version_id)
        return pd.read_sql_query(query.statement, session.connection(close_with_result=True))


class ViewOpenKeys(Base):
    __tablename__ = "drr_open_keys"

    property_code = Column(String, primary_key=True)
    data_type = Column(String, primary_key=True)
    start_release = Column(Integer)
    end_release = Column(Integer)

    @classmethod
    def get_keys(cls, session, dimension_codes, release_id):
        query = session.query(cls.property_code, cls.data_type)
        query = query.filter(cls.property_code.in_(dimension_codes))
        query = filter_by_release(query, cls.start_release, cls.end_release, release_id)
        data = pd.read_sql_query(query.statement, session.connection(close_with_result=True))
        return data

    @classmethod
    def get_all_keys(cls, session, release_id):
        query = session.query(cls.property_code, cls.data_type)
        query = filter_by_release(query, cls.start_release, cls.end_release, release_id)
        data = pd.read_sql_query(query.statement, session.connection(close_with_result=True))
        return data


class ViewDataTypes(Base):
    __tablename__ = "drr_data_types"

    datapoint = Column(String, primary_key=True)
    data_type = Column(String, primary_key=True)
    start_release = Column(Integer)
    end_release = Column(Integer)

    @classmethod
    def get_data_types(cls, session, datapoints, release_id):
        results = []
        batch_size = 2000
        batch_start = 0

        while batch_start < len(datapoints):
            batch_end = batch_start + batch_size
            datapoints_batch = datapoints[batch_start:batch_end]
            query = session.query(cls.datapoint, cls.data_type)
            query = filter_by_release(query, cls.start_release, cls.end_release, release_id)
            query = query.filter(cls.datapoint.in_(datapoints_batch))
            results.append(pd.read_sql_query(query.statement, session.connection(close_with_result=True)))
            batch_start += batch_size

        data = pd.concat(results, axis=0)
        return data

class ViewSubcategoryItemInfo(Base):
    __tablename__ = "drr_subcategory_item_info"

    subcategory_id = Column(Integer, primary_key=True)
    item_code = Column(String, primary_key=True)
    is_default_item = Column(Boolean)
    parent_item_code = Column(String)
    ordering = Column(Integer)
    arithmetic_operator = Column(String, nullable=True)
    comparison_symbol = Column(String, nullable=True)
    start_release_id = Column(Integer)
    end_release_id = Column(Integer)

    @classmethod
    def get_info(cls, session, subcategory_id, release_id=None):
        query = session.query(cls.item_code, cls.is_default_item, cls.parent_item_code,
                              cls.ordering,
                              cls.arithmetic_operator,
                              cls.comparison_symbol).filter(cls.subcategory_id == subcategory_id)
        query = filter_by_release(query, cls.start_release_id, cls.end_release_id, release_id)
        query = query.order_by(cls.ordering)
        data = pd.read_sql_query(query.statement, session.connection(close_with_result=True))
        return data

class ViewHierarchyVariables(Base):
    __tablename__ = "drr_hierarchy_variables"

    subcategory_id = Column(Integer, primary_key=True)
    variable_vid = Column(Integer, primary_key=True)
    main_property_code = Column(String, primary_key=True)
    context_property_code = Column(String)
    cell_code = Column(String)
    item_code = Column(String)
    start_release_id = Column(Integer)
    end_release_id = Column(Integer)

    @classmethod
    def get_subcategory_data(cls, session, subcategory_id, release_id):
        query = session.query(cls.cell_code, cls.variable_vid, cls.main_property_code,
                              cls.context_property_code,
                              cls.item_code).filter(
            cls.subcategory_id == subcategory_id)
        query = filter_by_release(query, cls.start_release_id, cls.end_release_id, release_id)
        data = pd.read_sql_query(query.statement, session.connection(close_with_result=True))
        return data


class ViewHierarchyVariablesContext(Base):
    __tablename__ = "drr_hierarchy_variables_context"

    variable_vid = Column(Integer, primary_key=True)
    context_property_code = Column(String, primary_key=True)
    item_code = Column(String)
    start_release_id = Column(Integer)
    end_release_id = Column(Integer)

    @classmethod
    def get_context_from_variables(cls, session, variables: List[int], release_id=None):
        # Make batches of 1000 variables
        results = []
        batch_size = 1000
        for i in range(0, len(variables), batch_size):
            batch_end = i + batch_size
            variables_batch = variables[i:batch_end]
            query = session.query(cls.variable_vid, cls.context_property_code, cls.item_code).filter(
                cls.variable_vid.in_(variables_batch))
            query = filter_by_release(query, cls.start_release_id, cls.end_release_id, release_id)
            results.append(pd.read_sql_query(query.statement, session.connection(close_with_result=True)))
        data = pd.concat(results, axis=0)
        # Removing duplicates to avoid issues later with default values
        data = data.drop_duplicates(keep='first').reset_index(drop=True)
        return data

class ViewHierarchyPreconditions(Base):
    __tablename__ = "drr_hierarchy_preconditions"

    expression = Column(NVARCHAR, primary_key=True)
    operation_code = Column(NVARCHAR, primary_key=True)
    variable_code = Column(NVARCHAR, primary_key=True)

    @classmethod
    def get_preconditions(cls, session):
        query = session.query(cls)
        return pd.read_sql_query(query.statement, session.connection(close_with_result=True))

class ViewOperations(Base):  # TODO: Review this class
    __tablename__ = "drr_operations"

    operation_version_id = Column(Integer, primary_key=True)
    operation_code = Column(String)
    expression = Column(String)
    start_release = Column(Integer)
    end_release = Column(Integer)
    precondition_operation_version_id = Column(Integer)

    @classmethod
    def get_operations(cls, session):
        query = session.query(cls).distinct()
        # query = filter_by_release(query, cls.start_release, cls.end_release, None).distinct()
        operations = pd.read_sql_query(query.statement, session.connection(close_with_result=True))
        return operations.to_dict(orient="records")

    @classmethod
    def get_expression_from_operation_code(cls, session, operation_code):
        query = session.query(cls.expression).filter(cls.operation_code == operation_code)
        query = filter_by_release(query, cls.start_release, cls.end_release, None)
        return query.one_or_none()

    @classmethod
    def get_preconditions_used(cls, session):
        query = session.query(cls)
        preconditions = query.filter(cls.operation_version_id.is_not(None)).distinct().all()
        preconditions_ids = list(set([p.precondition_operation_version_id for p in
                                      query.filter(cls.precondition_operation_version_id.is_not(None)).distinct().all()]))
        query = session.query(cls)

        query = query.filter(cls.operation_version_id.in_(preconditions_ids)).distinct()
        preconditions = pd.read_sql_query(query.statement, session.connection(close_with_result=True))

        return preconditions.to_dict(orient="records")


class ViewModules(Base):
    __tablename__ = "drr_module_from_table"

    module_code = Column(String, primary_key=True)
    table_code = Column(String, primary_key=True)
    from_date = Column(Date)
    to_date = Column(Date)

    @classmethod
    def get_all_modules(cls, session):
        query = session.query(cls.module_code, cls.table_code).distinct()

        return pd.read_sql_query(query.statement, session.connection(close_with_result=True))

    @classmethod
    def get_modules(cls, session, tables, release_id=None):
        query = session.query(cls.module_code, cls.table_code)
        # query = filter_by_release(query, cls.start_release, cls.end_release, release_id)
        query = query.filter(cls.table_code.in_(tables))
        result = query.all()
        if len(result) == 0:
            return []
        module_list = [r[0] for r in result]
        return list(set(module_list))


class ViewOperationFromModule(Base):
    __tablename__ = "drr_operation_versions_from_module_version"

    module_version_id = Column(Integer, primary_key=True)
    operation_version_id = Column(Integer, primary_key=True)
    module_code = Column(String)
    from_date = Column(Date)
    to_date = Column(Date)
    expression = Column(String)
    operation_code = Column(String)
    precondition_operation_version_id = Column(Integer)
    is_active = Column(Boolean, nullable=False)
    severity = Column(NVARCHAR(20), nullable=False)
    operation_scope_id = Column(Integer)

    @classmethod
    def get_operations(cls, session, module_code, ref_date):  # To be used in module dependencies
        query = session.query(
            cls.module_code, cls.from_date, cls.to_date, cls.expression, cls.operation_code, cls.operation_version_id)
        query = query.filter(cls.module_code == module_code)
        query = filter_by_date(query, cls.from_date, cls.to_date, ref_date)

        return pd.read_sql_query(query.statement, session.connection(close_with_result=True)).to_dict(orient="records")

    @classmethod
    def get_module_version_id_from_operation_vid(cls, session, operation_version_id):  # To be used in module dependencies
        query = session.query(cls.module_version_id, cls.module_code, cls.from_date, cls.to_date)
        query = query.filter(cls.operation_version_id == operation_version_id).distinct()

        return pd.read_sql_query(query.statement, session.connection(close_with_result=True)).to_dict(orient="records")

    @classmethod
    def get_operations_from_moduleversion_id(cls, session, module_version_id, with_preconditions=True, with_errors=False):
        query = session.query(
            cls.module_code, cls.from_date, cls.to_date, cls.expression, cls.operation_code, cls.operation_version_id,
            cls.precondition_operation_version_id, cls.is_active, cls.severity)
        query = query.filter(cls.module_version_id == module_version_id).distinct()
        reference = pd.read_sql_query(query.statement, session.connection(close_with_result=True))
        not_errors = []
        preconditions_to_remove = []
        if not with_errors:
            not_errors = session.query(OperationNode.OperationVID.label('operation_version_id')).distinct()
            not_errors = pd.read_sql_query(not_errors.statement, session.connection(close_with_result=True))
            not_errors = list(not_errors['operation_version_id'])
            reference = reference[reference['operation_version_id'].isin(not_errors)]
        if not with_preconditions:
            preconditions = session.query(ViewPreconditionInfo.operation_version_id).distinct()
            preconditions = pd.read_sql_query(preconditions.statement, session.connection(close_with_result=True))
            preconditions_to_remove = list(preconditions['operation_version_id'])
            reference = reference[~reference['operation_version_id'].isin(preconditions_to_remove)]

        return reference.to_dict(orient="records")

    @classmethod
    def get_composition_from_moduleversion_id(cls, session, module_version_id):  # TODO: Redo this one
        query = session.query(
            cls.module_code, cls.from_date, cls.to_date, cls.expression, cls.operation_code, cls.operation_version_id,
            cls.precondition_operation_version_id, cls.operation_scope_id)
        query = query.filter(cls.module_version_id == module_version_id)

        return pd.read_sql_query(query.statement, session.connection(close_with_result=True)).to_dict(orient="records")

    @classmethod
    def get_composition_from_operation_version_id(cls, session, operation_version_id):  # TODO: Redo this one
        query = session.query(
            cls.module_code, cls.module_version_id, cls.from_date, cls.to_date, cls.expression, cls.operation_code,
            cls.operation_version_id, cls.precondition_operation_version_id, cls.operation_scope_id)
        query = query.filter(cls.operation_version_id == operation_version_id)

        return pd.read_sql_query(query.statement, session.connection(close_with_result=True)).to_dict(orient="records")

    @classmethod
    def get_related_modules(cls, session, module_version_id):
        subquery = session.query(cls.operation_scope_id).filter(cls.module_version_id == module_version_id).distinct()
        query = session.query(cls).filter(and_(cls.operation_scope_id.in_(subquery), cls.module_version_id != module_version_id)).distinct()
        preconditions = session.query(ViewPreconditionInfo.operation_version_id).distinct()
        query = query.filter(cls.operation_version_id.notin_(preconditions)).distinct()
        related_modules = pd.read_sql_query(query.statement, session.connection(close_with_result=True))

        return related_modules.to_dict(orient="records")

    @classmethod
    def get_time_related_operations_version_id(cls, session, module_version_id):
        time_related = session.query(OperationNode.OperationVID.label('operation_version_id')).filter(
            OperationNode.OperatorID == 32).distinct()
        query = session.query(cls).filter(
            and_(cls.operation_version_id.in_(time_related), cls.module_version_id == module_version_id)).distinct()
        not_errors = session.query(OperationNode.OperationVID.label('operation_version_id')).distinct()
        query = query.filter(cls.operation_version_id.in_(not_errors)).distinct()

        return pd.read_sql_query(query.statement, session.connection(close_with_result=True)).to_dict(orient="records")


class ViewOperationInfo(Base):
    __tablename__ = "drr_operation_info"

    operation_node_id = Column(Integer, primary_key=True)
    operation_version_id = Column(Integer)
    parent_node_id = Column(Integer)
    operator_id = Column(Integer)
    symbol = Column(NVARCHAR(20))
    argument = Column(NVARCHAR(50))
    operator_argument_order = Column(Integer)
    is_leaf = Column(Boolean, nullable=False, unique=False)
    scalar = Column(String)
    operand_reference_id = Column(Integer, nullable=False, unique=False)
    operand_reference = Column(String)
    x = Column(Integer)
    y = Column(Integer)
    z = Column(Integer)
    item_id = Column(Integer)
    property_id = Column(Integer)
    variable_id = Column(Integer)
    use_interval_arithmetics = Column(Boolean, nullable=False, unique=False)
    fallback_value = Column(NVARCHAR(50))

    @classmethod
    def get_operation_info(cls, session, operation_version_id):
        query = session.query(cls).filter(cls.operation_version_id == operation_version_id)

        return pd.read_sql_query(query.statement, session.connection(close_with_result=True)).to_dict(orient="records")

    @classmethod
    def get_operation_info_df(cls, session, operation_version_ids):
        rename_dict = {
            "operation_node_id": "NodeID",
            "operation_version_id": "OperationVID",
            "operator_id": "OperatorID",
            "operator_argument_order": "Order",
            "parent_node_id": "ParentNodeID",
            "symbol": "symbol",
            "argument": "argument",
            "operand_reference": "OperandReference",
            "use_interval_arithmetics": "UseIntervalArithmetics",
            "fallback_value": "FallbackValue",
            "operand_reference_id": "OperandReferenceId",
            "scalar": "Scalar",
            "is_leaf": "IsLeaf",
            "item_id": "ItemID",
            "property_id": "PropertyID",
            "variable_id": "VariableID"
        }
        query = session.query(cls).filter(cls.operation_version_id.in_(operation_version_ids))
        df = pd.read_sql_query(query.statement, session.connection(close_with_result=True))
        df = df.rename(columns=rename_dict)

        return df


class ViewTableInfo(Base):
    __tablename__ = "drr_table_info"

    table_code = Column(String, primary_key=True)
    table_version_id = Column(Integer, primary_key=True)
    table_id = Column(Integer)
    module_code = Column(String)
    module_version_id = Column(Integer)
    variable_id = Column(Integer)
    variable_version_id = Column(Integer)

    @classmethod
    def get_tables_from_module_code(cls, session, module_code):
        query = session.query(cls.table_code, cls.table_version_id).filter(cls.module_code == module_code).distinct()

        return pd.read_sql_query(query.statement, session.connection(close_with_result=True)).to_dict(orient="records")

    @classmethod
    def get_tables_from_module_version(cls, session, module_version_id):
        query = session.query(cls.table_code, cls.table_version_id).filter(cls.module_version_id == module_version_id).distinct()

        return pd.read_sql_query(query.statement, session.connection(close_with_result=True)).to_dict(orient="records")

    @classmethod
    def get_variables_from_table_code(cls, session, table_code, to_dict=True):
        query = session.query(cls.variable_id, cls.variable_version_id).filter(cls.table_code == table_code)

        data = pd.read_sql_query(query.statement, session.connection(close_with_result=True))
        if to_dict:
            return data.to_dict(orient="records")
        return data

    @classmethod
    def get_variables_from_table_version(cls, session, table_version_id):
        query = session.query(cls.variable_id, cls.variable_version_id).filter(cls.table_version_id == table_version_id)

        return pd.read_sql_query(query.statement, session.connection(close_with_result=True)).to_dict(orient="records")

    @classmethod
    def get_intra_module_variables(cls, session):
        # We add distinct to ensure we only get same combination of module and variable_version_id once
        query = session.query(cls.variable_version_id, cls.module_code).distinct()
        module_data = pd.read_sql_query(query.statement, session.connection(close_with_result=True))
        # We drop duplicates to get only the variables that are not shared between modules
        intra_module_data = module_data.drop_duplicates(subset=["variable_version_id"], keep=False,
                                                        ignore_index=True)
        del module_data
        intra_module_variables = intra_module_data['variable_version_id'].unique().tolist()
        del intra_module_data
        return intra_module_variables

    @classmethod
    def is_intra_module(cls, session, table_codes):
        query = session.query(cls.table_code, cls.module_code).distinct().filter(cls.table_code.in_(table_codes))
        module_data = pd.read_sql_query(query.statement, session.connection(close_with_result=True))
        # if len(module_data["module_code"].unique()) == 1:
        #     return True
        all_combinations = module_data.groupby("table_code")["module_code"].apply(list).reset_index(
            drop=False).to_dict(orient="records")

        intersect_set = None
        for combination in all_combinations:
            if intersect_set is None:
                intersect_set = set(combination['module_code'])
            else:
                intersect_set = intersect_set.intersection(set(combination['module_code']))

        if intersect_set is None:
            return False
        return len(intersect_set) > 0


class ViewPreconditionInfo(Base):
    __tablename__ = "drr_precondition_info"

    operation_node_id = Column(Integer, primary_key=True)
    operation_version_id = Column(Integer)
    operation_code = Column(String)
    variable_type = Column(String)
    variable_id = Column(Integer)
    variable_version_id = Column(Integer)
    variable_code = Column(String)

    @classmethod
    def get_preconditions(cls, session):
        query = session.query(cls.operation_version_id, cls.operation_code, cls.variable_code).distinct()

        return pd.read_sql_query(query.statement, session.connection(close_with_result=True)).to_dict(orient="records")

    @classmethod
    def get_precondition_code(cls, session, variable_version_id):
        query = session.query(cls.variable_code).filter(cls.variable_version_id == variable_version_id).distinct()
        return query.one()

class ViewHierarchyOperandReferenceInfo(Base):
    __tablename__ = "drr_hierarchy_operand_reference_info"

    operation_code = Column(NVARCHAR, primary_key=True)
    operation_node_id = Column(Integer, primary_key=True)
    cell_id = Column(Integer, primary_key=True)
    variable_id = Column(Integer)

    @classmethod
    def get_operations(cls, session, cell_id):
        query = session.query(cls.operation_code, cls.operation_node_id).filter(cls.cell_id == cell_id).distinct()
        operations = pd.read_sql_query(query.statement, session.connection(close_with_result=True)).to_dict(orient="records")
        return operations

    @classmethod
    def get_hierarchy_operations(cls, session, var_id_list):
        query = session.query(cls).filter(cls.variable_id.in_(var_id_list))
        possible_op_codes = []

        df = pd.read_sql_query(query.statement, session.connection(close_with_result=True))
        grouped_code = df.groupby("operation_code")
        for elto_k, elto_v in grouped_code.groups.items(): # TODO: change for iterate only over keys
            if len(grouped_code.groups[elto_k]) == len(var_id_list):
                possible_op_codes.append(elto_k)
        return possible_op_codes

    @classmethod
    def get_cell_hierarchy_operations(cls, session, cell_id_list):
        query = session.query(cls).filter(cls.cell_id.in_(cell_id_list))
        possible_op_codes = []

        df = pd.read_sql_query(query.statement, session.connection(close_with_result=True))
        operation_codes = df["operation_code"].unique().tolist()
        for op_code in operation_codes:
            cell_ids_from_code = cls.get_hierarchy_operation_by_code(session, op_code)["cell_id"].unique().tolist()
            if set(cell_ids_from_code) == set(cell_id_list):
                possible_op_codes.append(op_code)
        return possible_op_codes

    @classmethod
    def get_cell_hierarchy_operations_posible_options(cls, session, cell_id_list):
        query = session.query(cls).filter(cls.cell_id.in_(cell_id_list))
        possible_op_codes = []

        df = pd.read_sql_query(query.statement, session.connection(close_with_result=True))
        operation_codes = df["operation_code"].unique().tolist()
        for op_code in operation_codes:
            possible_op_codes.append(op_code)
        return possible_op_codes

    @classmethod
    def get_hierarchy_operation_by_code(cls, session, operation_code):
        query = session.query(cls).filter(cls.operation_code == operation_code)
        return pd.read_sql_query(query.statement, session.connection(close_with_result=True))


class ViewReportTypeOperandReferenceInfo(Base):
    __tablename__ = "drr_report_type_operand_reference_info"

    operation_code = Column(NVARCHAR, primary_key=True)
    operation_node_id = Column(Integer, primary_key=True)
    cell_id = Column(Integer, primary_key=True)
    variable_id = Column(Integer)
    report_type = Column(String)
    table_version_id = Column(Integer)
    table_version_vid = Column(Integer)
    sub_category_id = Column(Integer)

    @classmethod
    def get_operations(cls, session, cell_id):
        query = session.query(cls.operation_code, cls.operation_node_id).filter(cls.cell_id == cell_id).distinct()
        operations = pd.read_sql_query(query.statement, session.connection(close_with_result=True)).to_dict(orient="records")
        return operations

    @classmethod
    def get_info_by_report_type(cls, session, report_type=HIERARCHY):
        # query = session.query(cls.operation_code, cls.cell_id).filter(and_(cls.sub_category_id == sub_category_id, cls.report_type == report_type)).distinct()
        query = session.query(cls.operation_code, cls.cell_id, cls.variable_id).filter(
            cls.report_type == report_type)
        return pd.read_sql_query(query.statement, session.connection(close_with_result=True))

    @classmethod
    def get_signed_cells_and_operations_by_table_version_id(cls, session, table_version_id, report_type=SIGN):
        query = session.query(cls.operation_code, cls.cell_id, cls.variable_id).filter(and_(
            cls.table_version_vid == table_version_id, cls.report_type == report_type))
        return pd.read_sql_query(query.statement, session.connection(close_with_result=True))

    @classmethod
    def get_existence_cells_and_operations_by_table_version_id(cls, session, table_version_id, report_type=EXISTENCE):
        query = session.query(cls.operation_code, cls.cell_id, cls.variable_id).filter(and_(
            cls.table_version_vid == table_version_id, cls.report_type == report_type))
        return pd.read_sql_query(query.statement, session.connection(close_with_result=True))

    @classmethod
    def get_hierarchy_operations(cls, session, var_id_list):
        query = session.query(cls).filter(and_(cls.variable_id.in_(var_id_list), cls.report_type == HIERARCHY))
        possible_op_codes = []

        df = pd.read_sql_query(query.statement, session.connection(close_with_result=True))
        grouped_var = df.groupby("variable_id")
        grouped_code = df.groupby("operation_code")
        for elto_k, elto_v in grouped_code.groups.items(): # TODO: change for iterate only over keys
            if len(grouped_code.groups[elto_k]) == len(var_id_list):
                possible_op_codes.append(elto_k)
        return possible_op_codes

    @classmethod
    def get_cell_hierarchy_operations(cls, session, cell_id_list):
        query = session.query(cls).filter(and_(cls.cell_id.in_(cell_id_list), cls.report_type == HIERARCHY))
        possible_op_codes = []

        df = pd.read_sql_query(query.statement, session.connection(close_with_result=True))

        grouped_code = df.groupby("operation_code")
        for elto_k, elto_v in grouped_code.groups.items(): # TODO: change for iterate only over keys
            if len(grouped_code.groups[elto_k]) == len(cell_id_list):
                possible_op_codes.append(elto_k)
        return possible_op_codes

    @classmethod
    def get_existence_tables_vid(cls, session):
        query = session.query(cls.table_version_id).filter(cls.report_type == EXISTENCE).distinct()
        return pd.read_sql_query(query.statement, session.connection(close_with_result=True))

    @classmethod
    def get_cell_report_operations(cls, session, cell_id_list, report_type):
        query = session.query(cls).filter(and_(cls.cell_id.in_(cell_id_list), cls.report_type == report_type))
        matched_op_codes = []

        df = pd.read_sql_query(query.statement, session.connection(close_with_result=True))
        operation_codes = df["operation_code"].unique().tolist()
        for op_code in operation_codes:
            cell_ids_from_code = cls.get_report_operation_by_code(session, op_code)["cell_id"].unique().tolist()
            if set(cell_ids_from_code) == set(cell_id_list):
                matched_op_codes.append(op_code)
        return matched_op_codes

    @classmethod
    def get_report_operation_by_code(cls, session, operation_code):
        query = session.query(cls).filter(cls.operation_code == operation_code)
        return pd.read_sql_query(query.statement, session.connection(close_with_result=True))

    @classmethod
    def get_sign_info_by_table_version_vid(cls, session, table_version_vid):
        query = session.query(cls).filter(and_(cls.table_version_vid == table_version_vid, cls.report_type == SIGN))
        df = pd.read_sql_query(query.statement, session.connection(close_with_result=True))
        aux_dict = {}
        for key, group in df.groupby("operation_code"):
            aux_dict[key] = {}
            aux_dict[key]["cell_id"] = group["cell_id"].tolist()
            aux_dict[key]["variable_id"] = group["variable_id"].tolist()

        return aux_dict

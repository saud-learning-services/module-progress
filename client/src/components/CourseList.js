import {
  List,
  Datagrid,
  TextField,
  EditButton,
  DeleteButton,
  ArrayField,
  SingleFieldList,
  ChipField,
} from "react-admin";

const CourseList = (props) => {
  return (
    <List title="Module Progress User Management Console" {...props}>
      <Datagrid>
        <TextField label="Course Id" source="id" />
        <TextField label="Course Name" source="course_name" />
        <ArrayField labels="Users" source="users">
          <SingleFieldList linkType={false}>
            <ChipField source="name" />
          </SingleFieldList>
        </ArrayField>
        <EditButton basePath="/courses" />
        <DeleteButton basePath="/courses" />
      </Datagrid>
    </List>
  );
};

export default CourseList;
